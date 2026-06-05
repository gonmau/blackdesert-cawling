#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, requests, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

TARGET_COUNTRIES = {
    "us": "미국", "gb": "영국", "de": "독일", "fr": "프랑스", "ca": "캐나다",
    "br": "브라질", "jp": "일본", "kr": "한국", "cn": "중국", "ru": "러시아",
    "au": "호주", "es": "스페인", "it": "이탈리아", "pl": "폴란드", "tr": "터키",
    "nl": "네덜란드", "se": "스웨덴", "no": "노르웨이", "dk": "덴마크", "fi": "핀란드",
    "at": "오스트리아", "ch": "스위스", "cz": "체코", "sg": "싱가포르",
    "be": "벨기에", "hk": "홍콩", "nz": "뉴질랜드", "tw": "대만", "th": "태국"
}

STEAM_APP_IDS = {"3321460"}
DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "crimson_desert_rivals.json"
HISTORY_FILE = DATA_DIR / "history.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

REQUEST_DELAY = 1.5   # 요청 간 기본 딜레이 (초)
MAX_RETRIES   = 3     # 429/403 시 재시도 횟수
RETRY_WAIT    = 10    # 재시도 대기 (초), 매번 2배씩 증가

def get_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fetch_with_retry(url):
    """429/403 자동 재시도 포함 GET 요청"""
    wait = RETRY_WAIT
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code == 429:
                print(f"    ⏳ 429 차단 — {wait}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                wait *= 2
                continue
            if res.status_code == 403:
                print(f"    🚫 403 차단 — {wait}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                wait *= 2
                continue
            res.raise_for_status()
            return res
        except requests.RequestException as e:
            print(f"    ❌ 요청 오류: {e}")
            time.sleep(wait)
            wait *= 2
    return None

def parse_price_from_html(item):
    """HTML에서 직접 가격/할인 정보 파싱"""
    price_div = item.select_one(".search_price")
    if not price_div:
        return {"is_free": False, "is_discounted": False}

    price_text = price_div.get_text(strip=True).lower()
    is_free = "free" in price_text

    discount_block = item.select_one(".search_discount")
    is_discounted = False
    if discount_block:
        pct_text = discount_block.get_text(strip=True)
        is_discounted = pct_text.startswith("-") and not is_free

    return {"is_free": bool(is_free), "is_discounted": is_discounted}

def analyze_country(cc, name, history, idx, total):
    """단일 국가 순차 처리"""
    all_items = []
    crimson_rank = None
    crimson_rank_diff = 0

    print(f"[{idx:02d}/{total}] 🔍 {name} ({cc})")

    for page in range(1, 6):
        url = f"https://store.steampowered.com/search/?filter=topsellers&cc={cc}&page={page}"
        res = fetch_with_retry(url)
        if res is None:
            print(f"         ❌ {page}페이지 실패, 건너뜀")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("#search_resultsRows > a")
        if not items:
            break

        for item in items:
            appid = item.get("data-ds-appid", "")
            name_el = item.select_one(".title")
            name_game = name_el.text.strip() if name_el else "Unknown"
            price_info = parse_price_from_html(item)

            current_rank = len(all_items) + 1
            prev_rank = history.get(cc, {}).get(appid, current_rank)

            all_items.append({
                "app_id": appid,
                "name": name_game,
                "is_free": price_info["is_free"],
                "is_discounted": price_info["is_discounted"],
                "rank": current_rank,
                "rank_diff": prev_rank - current_rank,
            })

            if appid in STEAM_APP_IDS:
                crimson_rank = current_rank
                crimson_rank_diff = prev_rank - current_rank
                break

        if crimson_rank:
            break

        time.sleep(REQUEST_DELAY)  # 페이지 간 딜레이

    rivals = [
        i for i in all_items
        if i["rank"] < (crimson_rank or 9999)
        and (i["is_free"] or i["is_discounted"])
    ]

    if crimson_rank:
        diff_str = f" (▲{crimson_rank_diff})" if crimson_rank_diff > 0 else \
                   f" (▼{abs(crimson_rank_diff)})" if crimson_rank_diff < 0 else ""
        print(f"         ✅ {crimson_rank}위{diff_str}, 경쟁작 {len(rivals)}개")
    else:
        print(f"         ⚠️  100위 밖")

    return (
        {"crimson_desert_rank": crimson_rank, "rank_diff": crimson_rank_diff, "rivals": rivals},
        {i["app_id"]: i["rank"] for i in all_items},
    )

if __name__ == "__main__":
    target = {
        cc: name for cc, name in TARGET_COUNTRIES.items()
        if not sys.argv[1:] or cc in sys.argv[1:]
    }

    DATA_DIR.mkdir(exist_ok=True)
    history = get_history()

    results = {
        "generated_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "countries": {},
    }
    new_history = {}
    total = len(target)

    # ← ThreadPoolExecutor 제거, 완전 순차 처리
    for idx, (cc, name) in enumerate(target.items(), 1):
        result, country_history = analyze_country(cc, name, history, idx, total)
        results["countries"][cc] = {"name": name, **result}
        new_history[cc] = country_history
        time.sleep(REQUEST_DELAY)  # 국가 간 딜레이

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    print(f"\n💾 저장 완료: {OUTPUT_FILE}")