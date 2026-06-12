#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam Global Top Sellers - 붉은사막 경쟁작 추적기
붉은사막(3321460)보다 상위에 있는 무료/할인 게임만 추적
"""
import json, time, requests, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

CRIMSON_DESERT_APPID = "3321460"
DATA_DIR = Path("data")
OUTPUT_FILE       = DATA_DIR / "global_rivals.json"
HISTORY_FILE      = DATA_DIR / "global_history.json"
RANK_HISTORY_FILE = DATA_DIR / "global_rank_history.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MAX_RETRIES = 3
REQUEST_DELAY = 1.5
MAX_RANK_HISTORY = 180   # 6h 간격 × 180 ≈ 45일


def get_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_rank_history():
    if RANK_HISTORY_FILE.exists():
        with open(RANK_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def extract_appid(logo_url):
    m = re.search(r"/apps/(\d+)/", logo_url or "")
    return m.group(1) if m else ""


def fetch_globaltopsellers(start=0, count=100):
    url = (
        f"https://store.steampowered.com/search/results/"
        f"?query&start={start}&count={count}&filter=globaltopsellers&json=1"
    )
    wait = 10
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code in (429, 403):
                print(f"  ⏳ {res.status_code} — {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                wait *= 2
                continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            time.sleep(wait)
            wait *= 2
    return None


def get_price_info(appid):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us"
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json().get(str(appid), {})
        if not data.get("success"):
            return {"is_free": False, "is_discounted": False, "discount_pct": 0}
        app_data = data.get("data", {})
        is_free = bool(app_data.get("is_free", False))
        price = app_data.get("price_overview") or {}
        discount_pct = price.get("discount_percent", 0)
        is_discounted = discount_pct > 0 and not is_free
        return {"is_free": is_free, "is_discounted": is_discounted, "discount_pct": discount_pct}
    except:
        return {"is_free": False, "is_discounted": False, "discount_pct": 0}


def run():
    DATA_DIR.mkdir(exist_ok=True)
    history = get_history()
    rank_history = get_rank_history()

    print("🔍 Steam Global Top Sellers 수집 중...")

    # ── 1단계: 전체 목록 수집 (붉은사막 발견까지) ──────────────────
    raw_items = []   # API에서 받은 순서 그대로
    crimson_idx = None  # raw_items 내 0-based index

    for start in [0, 100, 200]:
        data = fetch_globaltopsellers(start=start, count=100)
        if not data:
            print(f"  ❌ 응답 없음 (start={start})")
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            appid = extract_appid(item.get("logo", ""))
            raw_items.append({"app_id": appid, "name": item.get("name", "Unknown")})
            if appid == CRIMSON_DESERT_APPID:
                crimson_idx = len(raw_items) - 1
                break

        if crimson_idx is not None:
            break
        time.sleep(REQUEST_DELAY)

    now_str = datetime.now(timezone(timedelta(hours=9))).isoformat()

    # ── 2단계: 순위 계산 (index + 1 이 곧 순위) ────────────────────
    if crimson_idx is None:
        print("⚠️  300위 안에 붉은사막 없음")
        output = {"generated_at": now_str, "crimson_desert_rank": None, "rank_diff": 0, "rivals": []}
    else:
        crimson_rank = crimson_idx + 1   # 1-based 순위
        prev_cd_rank = history.get(CRIMSON_DESERT_APPID, crimson_rank)
        crimson_rank_diff = prev_cd_rank - crimson_rank
        diff_str = (f" (▲{crimson_rank_diff})" if crimson_rank_diff > 0
                    else f" (▼{abs(crimson_rank_diff)})" if crimson_rank_diff < 0 else "")
        print(f"✅ 붉은사막 글로벌 {crimson_rank}위{diff_str}")

        # ── 3단계: 붉은사막 앞 게임들 가격 조회 ───────────────────
        rivals = []
        print(f"💰 상위 {crimson_rank - 1}개 게임 가격 조회 중...")
        for idx, item in enumerate(raw_items[:crimson_idx]):   # 붉은사막 앞까지만
            appid = item["app_id"]
            rank = idx + 1
            prev_rank = history.get(appid, rank)

            if not appid:
                continue

            price = get_price_info(appid)
            if price["is_free"] or price["is_discounted"]:
                rivals.append({
                    "app_id": appid,
                    "name": item["name"],
                    "rank": rank,
                    "rank_diff": prev_rank - rank,
                    **price,
                })
            time.sleep(0.3)

        print(f"📊 경쟁작(무료/할인): {len(rivals)}개")

        # 순위 시계열 누적
        rank_history.append({"t": now_str, "rank": crimson_rank})
        if len(rank_history) > MAX_RANK_HISTORY:
            rank_history = rank_history[-MAX_RANK_HISTORY:]

        output = {
            "generated_at": now_str,
            "crimson_desert_rank": crimson_rank,
            "rank_diff": crimson_rank_diff,
            "rivals": rivals,
        }

    # ── 4단계: 저장 ────────────────────────────────────────────────
    new_history = {item["app_id"]: (i + 1) for i, item in enumerate(raw_items) if item["app_id"]}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
    with open(RANK_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(rank_history, f, ensure_ascii=False, indent=2)

    print(f"💾 저장 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
