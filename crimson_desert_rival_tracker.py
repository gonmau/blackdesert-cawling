#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, requests, sys, re
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

def extract_appid_from_logo(logo_url):
    m = re.search(r"/apps/(\d+)/", logo_url or "")
    return m.group(1) if m else ""

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

def get_price_info(appid, cc):
    """가격/무료/할인 정보 조회"""
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc={cc}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json().get(str(appid), {})
        if not data.get("success"):
            return {"is_free": False, "is_discounted": False, "discount_pct": 0}

        app_data = data.get("data", {})

        # is_free 필드만 신뢰 — True면 F2P
        is_free = bool(app_data.get("is_free", False))

        # 할인: price_overview 있고 discount_percent > 0
        price = app_data.get("price_overview") or {}
        discount_pct = price.get("discount_percent", 0)
        is_discounted = discount_pct > 0 and not is_free

        return {
            "is_free": is_free,
            "is_discounted": is_discounted,
            "discount_pct": discount_pct,
        }
    except:
        return {"is_free": False, "is_discounted": False, "discount_pct": 0}

def analyze_country(cc, name, history, idx, total):
    print(f"[{idx:02d}/{total}] 🔍 {name} ({cc})")

    all_items = []
    crimson_rank = None
    crimson_rank_diff = 0

    for start in [0, 100, 200]:
        data = fetch_topsellers(cc, start=start, count=100)
        if not data:
            print(f"    ❌ 응답 없음 (start={start})")
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            logo = item.get("logo", "")
            appid = extract_appid_from_logo(logo)
            name_game = item.get("name", "Unknown")
            current_rank = len(all_items) + 1
            prev_rank = history.get(cc, {}).get(appid, current_rank)

            all_items.append({
                "app_id": appid,
                "name": name_game,
                "is_free": False,
                "is_discounted": False,
                "discount_pct": 0,
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

    # 붉은사막 못 찾으면 종료
    if crimson_rank is None:
        print(f"         ⚠️  300위 밖 (붉은사막 미발견)")
        return (
            {"crimson_desert_rank": None, "rank_diff": 0, "rivals": []},
            {i["app_id"]: i["rank"] for i in all_items},
        )

    # 붉은사막 앞 순위 게임만 가격 조회
    rivals = []
    for item in all_items[:crimson_rank - 1]:
        if not item["app_id"]:
            continue
        price = get_price_info(item["app_id"], cc)
        item.update(price)
        if item["is_free"] or item["is_discounted"]:
            rivals.append(item)
        time.sleep(0.3)

    diff_str = (f" (▲{crimson_rank_diff})" if crimson_rank_diff > 0
                else f" (▼{abs(crimson_rank_diff)})" if crimson_rank_diff < 0 else "")
    print(f"         ✅ {crimson_rank}위{diff_str}, 경쟁작 {len(rivals)}개")

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
