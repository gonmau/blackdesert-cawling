#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, requests, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

TARGET_COUNTRIES = {
    "us": "미국", "gb": "영국", "de": "독일", "fr": "프랑스", "ca": "캐나다",
    "br": "브라질", "jp": "일본", "kr": "한국", "cn": "중국", "ru": "러시아",
    "au": "호주", "es": "스페인", "it": "이탈리아", "pl": "폴란드", "tr": "터키",
    "nl": "네덜란드", "se": "스웨덴", "no": "노르웨이", "dk": "덴마크", "fi": "핀란드",
    "at": "오스트리아", "ch": "스위스", "cz": "체코", "sg": "싱가포르",
    "be": "벨기에", "hk": "홍콩", "nz": "뉴질랜드", "tw": "대만", "th": "태국"
}

CRIMSON_DESERT_APPID = "3321460"
DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "crimson_desert_rivals.json"
HISTORY_FILE = DATA_DIR / "history.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

REQUEST_DELAY = 1.5
MAX_RETRIES = 3

def get_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fetch_topsellers(cc, start=0, count=100):
    url = (
        f"https://store.steampowered.com/search/results/"
        f"?query&start={start}&count={count}&filter=topsellers&cc={cc}&json=1"
    )
    wait = 10
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code in (429, 403):
                print(f"    ⏳ {res.status_code} — {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                wait *= 2
                continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            time.sleep(wait)
            wait *= 2
    return None

def parse_item(item, rank, cc, history):
    """응답 item에서 필요한 정보 추출 — 필드명 유연하게 처리"""
    # app_id
    appid = str(
        item.get("app_id") or
        item.get("appid") or
        item.get("id") or
        item.get("data-ds-appid") or ""
    )

    # 게임명
    name_game = (
        item.get("name") or
        item.get("title") or
        item.get("app_name") or
        "Unknown"
    )

    # 무료 여부
    is_free = bool(
        item.get("is_free_game") or
        item.get("is_free") or
        (item.get("price") == 0) or
        (isinstance(item.get("price"), dict) and item["price"].get("original", 1) == 0)
    )

    # 할인 여부
    discount_pct = 0
    price = item.get("price") or {}
    if isinstance(price, dict):
        discount_pct = price.get("discount_pct", 0) or price.get("discount", 0) or 0
    elif item.get("discount_pct"):
        discount_pct = item.get("discount_pct", 0)
    is_discounted = discount_pct > 0 and not is_free

    prev_rank = history.get(cc, {}).get(appid, rank)

    return {
        "app_id": appid,
        "name": name_game,
        "is_free": is_free,
        "is_discounted": is_discounted,
        "discount_pct": discount_pct,
        "rank": rank,
        "rank_diff": prev_rank - rank,
    }

def analyze_country(cc, name, history, idx, total):
    print(f"[{idx:02d}/{total}] 🔍 {name} ({cc})")

    all_items = []
    crimson_rank = None
    crimson_rank_diff = 0

    for start in [0, 100]:
        data = fetch_topsellers(cc, start=start, count=100)
        if not data:
            print(f"    ❌ 응답 없음 (start={start})")
            break

        # items 키 유연하게 탐색
        items = (
            data.get("items") or
            data.get("results") or
            data.get("games") or
            []
        )

        if not items:
            print(f"    ⚠️  items 없음 — 응답 키: {list(data.keys())}")
            break

        for item in items:
            current_rank = len(all_items) + 1
            parsed = parse_item(item, current_rank, cc, history)
            all_items.append(parsed)

            if parsed["app_id"] == CRIMSON_DESERT_APPID:
                crimson_rank = current_rank
                crimson_rank_diff = parsed["rank_diff"]
                break

        if crimson_rank:
            break

        time.sleep(REQUEST_DELAY)

    rivals = [
        i for i in all_items
        if i["rank"] < (crimson_rank or 9999)
        and (i["is_free"] or i["is_discounted"])
    ]

    if crimson_rank:
        diff_str = (f" (▲{crimson_rank_diff})" if crimson_rank_diff > 0
                    else f" (▼{abs(crimson_rank_diff)})" if crimson_rank_diff < 0 else "")
        print(f"         ✅ {crimson_rank}위{diff_str}, 경쟁작 {len(rivals)}개")
    else:
        print(f"         ⚠️  150위 밖")

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

    for idx, (cc, name) in enumerate(target.items(), 1):
        result, country_history = analyze_country(cc, name, history, idx, total)
        results["countries"][cc] = {"name": name, **result}
        new_history[cc] = country_history
        time.sleep(REQUEST_DELAY)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    print(f"\n💾 저장 완료: {OUTPUT_FILE}")
