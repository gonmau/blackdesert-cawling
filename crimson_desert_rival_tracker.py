#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crimson_desert_rival_tracker.py
붉은사막보다 상위 순위의 무료/할인 게임 추적기

steam_topseller_tracker.py 와 동일한 API/파싱 방식 사용:
  - fetch_page(): search/results?json=1
  - appid 추출: logo URL에서 /steam/apps/(\\d+)/ 정규식
  - RETRY_DELAYS, COUNTRY_SLEEP, HEADERS 동일
가격 정보는 같은 item dict에서 추가 파싱 (name, price, discount_percent 등)
"""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ─── 설정 ─────────────────────────────────────────────────────────────────────

STEAM_APP_IDS = {"3321460"}   # Crimson Desert (기존 트래커와 동일)

OUTPUT_DIR  = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "crimson_desert_rivals.json"
OUTPUT_DIR.mkdir(exist_ok=True)

KST = timezone(timedelta(hours=9))

# 기존 steam_topseller_tracker.py 와 완전히 동일한 값
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

RETRY_DELAYS = {
    "cn": [10, 30, 60],
    "ru": [10, 30, 60],
}
DEFAULT_RETRY_DELAYS = [5, 15, 30]

COUNTRY_SLEEP = {
    "cn": 5,
    "ru": 5,
}
DEFAULT_COUNTRY_SLEEP = 1.5

TARGET_COUNTRIES = {
    "us": "미국",   "gb": "영국",   "de": "독일",   "fr": "프랑스",
    "ca": "캐나다", "br": "브라질", "jp": "일본",   "kr": "한국",
    "cn": "중국",   "ru": "러시아", "au": "호주",   "es": "스페인",
    "it": "이탈리아","pl": "폴란드","tr": "터키",   "nl": "네덜란드",
    "se": "스웨덴", "no": "노르웨이","dk": "덴마크","fi": "핀란드",
    "at": "오스트리아","ch": "스위스","cz": "체코", "sg": "싱가포르",
    "be": "벨기에", "hk": "홍콩",   "nz": "뉴질랜드","tw": "대만",
    "th": "태국",
}

COUNTRY_FLAGS = {
    "us":"🇺🇸","gb":"🇬🇧","de":"🇩🇪","fr":"🇫🇷","ca":"🇨🇦","br":"🇧🇷",
    "jp":"🇯🇵","kr":"🇰🇷","cn":"🇨🇳","ru":"🇷🇺","au":"🇦🇺","es":"🇪🇸",
    "it":"🇮🇹","pl":"🇵🇱","tr":"🇹🇷","nl":"🇳🇱","se":"🇸🇪","no":"🇳🇴",
    "dk":"🇩🇰","fi":"🇫🇮","at":"🇦🇹","ch":"🇨🇭","cz":"🇨🇿","sg":"🇸🇬",
    "be":"🇧🇪","hk":"🇭🇰","nz":"🇳🇿","tw":"🇹🇼","th":"🇹🇭",
}


# ─── Steam API (기존 fetch_page 완전 동일) ────────────────────────────────────

def fetch_page(cc: str, page: int, retry_delays: list) -> dict | None:
    url = "https://store.steampowered.com/search/results/"
    params = {"filter": "topsellers", "cc": cc, "l": "en", "json": 1, "page": page}

    for attempt, delay in enumerate([0] + retry_delays):
        if delay > 0:
            print(f"  ⏳ {cc} p{page} {delay}초 후 재시도 ({attempt}/{len(retry_delays)})...")
            time.sleep(delay)
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                print(f"  ⚠️ {cc} p{page} 429 Rate Limited")
                if attempt == len(retry_delays):
                    print(f"  ❌ {cc} p{page} 재시도 초과, 포기")
                    return None
                continue
            else:
                print(f"  ⚠️ {cc} p{page} 응답 실패: {r.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ {cc} p{page} 오류: {e}")
            return None
    return None


# ─── 가격 파싱 ────────────────────────────────────────────────────────────────

def parse_price_info(item: dict) -> dict:
    """
    search/results JSON item 에서 가격·할인 정보를 파싱.

    Steam search/results item 실제 필드 (HTML 파싱 결과):
      - "name"             : 게임명 문자열
      - "logo"             : capsule 이미지 URL  ← appid 추출용
      - "price"            : 가격 문자열  예) "₩ 66,000"  /  "Free to Play"
                             할인 중일 때는 원가(취소선)도 같은 필드에 포함될 수 있음
      - "discounted_price" : 할인가 문자열  예) "₩ 33,000"  (없으면 키 자체 없거나 None)
      - "discount_percent" : 할인율 문자열  예) "-50%"  (없으면 "" 또는 키 없음)
      - "reviews_total"    : 리뷰 수 (int)
      - "metascore"        : 메타스코어 (int/-1)
      - "type"             : "app" | "bundle" | ...

    반환 dict:
      app_id, name, original_price, final_price,
      discount_percent(int), is_free(bool), is_discounted(bool), store_url
    """
    # ── appid ──
    logo = item.get("logo", "")
    m = re.search(r"/steam/apps/(\d+)/", logo)
    appid = m.group(1) if m else ""

    name = item.get("name", "") or "Unknown"

    # ── 가격 문자열 ──
    raw_price = (item.get("price") or "").strip()
    raw_disc  = (item.get("discounted_price") or "").strip()
    disc_str  = (item.get("discount_percent") or "").strip()

    # Free to Play 판정
    is_free = any(kw in raw_price.lower() for kw in ["free", "무료"])

    # 할인율 숫자 추출  "-50%" → 50
    disc_pct = 0
    pct_m = re.search(r"(\d+)", disc_str)
    if pct_m:
        disc_pct = int(pct_m.group(1))

    # 할인 여부: 할인율 > 0  OR  discounted_price 가 있고 원가와 다름
    is_discounted = disc_pct > 0 or (bool(raw_disc) and raw_disc != raw_price)

    # 최종가격 결정
    if is_free:
        original_price = None
        final_price    = "Free"
    elif is_discounted and raw_disc:
        original_price = raw_price
        final_price    = raw_disc
    else:
        original_price = raw_price
        final_price    = raw_price

    return {
        "app_id":          appid,
        "name":            name,
        "original_price":  original_price,
        "final_price":     final_price,
        "discount_percent": disc_pct,
        "is_free":         is_free,
        "is_discounted":   is_discounted,
        "store_url":       f"https://store.steampowered.com/app/{appid}" if appid else "",
    }


# ─── 국가별 분석 ──────────────────────────────────────────────────────────────

def analyze_country(cc: str) -> dict:
    """
    기존 get_top_sellers 로직 그대로 유지하되,
    붉은사막 발견 전까지 각 item의 가격 정보도 함께 수집.
    """
    retry_delays = RETRY_DELAYS.get(cc, DEFAULT_RETRY_DELAYS)
    seen:      set[str]  = set()
    real_rank: int       = 0
    found:     bool      = False
    crimson_rank         = None
    candidates: list     = []   # 붉은사막 발견 전 누적 (가격 포함)

    for page in range(1, 11):
        data = fetch_page(cc, page, retry_delays)
        if data is None:
            break
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            # ── 기존 방식: logo에서 appid 추출 ──
            logo  = item.get("logo", "")
            m     = re.search(r"/steam/apps/(\d+)/", logo)
            appid = m.group(1) if m else ""
            if not appid or appid in seen:
                continue
            seen.add(appid)
            real_rank += 1

            if appid in STEAM_APP_IDS:
                crimson_rank = real_rank
                found = True
                break   # 붉은사막 발견 → 페이지 루프 탈출

            # 붉은사막 발견 전 → 가격 정보 파싱하여 후보 목록에 추가
            info = parse_price_info(item)
            info["rank"] = real_rank
            info["cc"]   = cc
            candidates.append(info)

        if found:
            break
        time.sleep(1.0)

    if real_rank == 0:
        print(f"  ⚠️ {cc} 데이터 없음")
        return {"cc": cc, "crimson_desert_rank": None, "rivals": [],
                "total_fetched": 0, "error": True, "not_charted": False}

    # 붉은사막보다 상위 중 무료 or 할인 게임만 추출
    rivals = [c for c in candidates if c["is_free"] or c["is_discounted"]]

    status = f"#{crimson_rank}" if crimson_rank else "순위권 밖"
    print(f"  ✅ {cc}: 총 {real_rank}개 파싱, Crimson Desert {status}, 경쟁 {len(rivals)}개")

    return {
        "cc":                  cc,
        "crimson_desert_rank": crimson_rank,
        "rivals":              rivals,
        "total_fetched":       real_rank,
        "not_charted":         crimson_rank is None,
        "error":               False,
    }


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def run_tracker(target_ccs: list[str] | None = None):
    if target_ccs is None:
        target_ccs = list(TARGET_COUNTRIES.keys())

    now_kst   = datetime.now(KST)
    timestamp = now_kst.isoformat()

    results = {
        "generated_at":          timestamp,
        "crimson_desert_app_id": list(STEAM_APP_IDS)[0],
        "countries":             {},
    }

    print("=" * 60)
    print(f"🎮 붉은사막 Steam 경쟁 트래커 ({len(target_ccs)}개국)")
    print(f"📅 {now_kst.strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 60)

    for cc in target_ccs:
        flag = COUNTRY_FLAGS.get(cc, "")
        name = TARGET_COUNTRIES.get(cc, cc.upper())
        print(f"\n🔍 {flag} {name} ({cc}) 수집 중...")

        result = analyze_country(cc)
        results["countries"][cc] = {"name": f"{flag} {name}", **result}

        sleep_sec = COUNTRY_SLEEP.get(cc, DEFAULT_COUNTRY_SLEEP)
        print(f"  💤 {sleep_sec}초 대기...")
        time.sleep(sleep_sec)

    # ── 저장 ──
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 저장 완료: {OUTPUT_FILE}")

    # ── 요약 ──
    charted = [(cc, d) for cc, d in results["countries"].items()
               if d.get("crimson_desert_rank")]
    print("\n" + "=" * 60)
    print(f"📊 순위권 진입: {len(charted)}/{len(target_ccs)}개국")
    for cc, d in sorted(charted, key=lambda x: x[1]["crimson_desert_rank"]):
        r  = d["crimson_desert_rank"]
        rv = len(d.get("rivals", []))
        print(f"  {d['name']}: #{r}  (경쟁 {rv}개)")

    not_charted = [(cc, d) for cc, d in results["countries"].items()
                   if d.get("not_charted") and not d.get("error")]
    if not_charted:
        names = ", ".join(d["name"] for _, d in not_charted)
        print(f"📭 순위권 밖: {names}")

    errors = [(cc, d) for cc, d in results["countries"].items() if d.get("error")]
    if errors:
        names = ", ".join(d["name"] for _, d in errors)
        print(f"❌ 수집 실패: {names}")

    return results


if __name__ == "__main__":
    import sys
    targets = [c.lower() for c in sys.argv[1:]] if len(sys.argv) > 1 else None
    run_tracker(targets)
