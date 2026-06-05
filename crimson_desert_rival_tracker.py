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
    """JSON API 엔드포인트 사용 — HTML 파싱 불필요"""
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

def analyze_country(cc, name, history, idx, total):
    print(f"[{idx:02d}/{total}] 🔍 {name} ({cc})")

    all_items = []
    crimson_rank = None
    crimson_rank_diff = 0

    # 최대 150개 (start=0, start=100)
    for start in [0, 100]:
        data = fetch_topsellers(cc, start=start, count=100)
        if not data:
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            appid = str(item.get("app_id") or item.get("id") or "")
            name_game = item.get("name", "Unknown")

            # 가격 정보 파싱
            price = item.get("price") or {}
            is_free = item.get("is_free_game", False) or price.get("original", 0) == 0
            discount_pct = price.get("discount_pct", 0) or 0
            is_discounted = discount_pct > 0 and not is_free

            current_rank = len(all_items) + 1
            prev_rank = history.get(cc, {}).get(appid, current_rank)

            all_items.append({
                "app_id": appid,
                "name": name_game,
                "is_free": bool(is_free),
                "is_discounted": bool(is_discounted),
                "discount_pct": discount_pct,
                "rank": current_rank,
                "rank_diff": prev_rank - current_rank,
            })

            if appid == CRIMSON_DESERT_APPID:
                crimson_rank = current_rank
                crimson_rank_diff = prev_rank - current_rank
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
