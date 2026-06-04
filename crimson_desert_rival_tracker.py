"""
crimson_desert_rival_tracker.py
붉은사막(Crimson Desert)보다 상위 순위의 무료/할인 게임 추적기
Steam Top Sellers API를 각국별로 조회하여 분석
"""

import requests
import json
import time
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── 설정 ────────────────────────────────────────────────────────────────────

CRIMSON_DESERT_APP_ID = 1143720
CRIMSON_DESERT_NAMES = ["crimson desert", "붉은사막"]

# 추적할 국가 목록 (cc 코드 + 표시명)
COUNTRIES = {
    "KR": "🇰🇷 한국",
    "US": "🇺🇸 미국",
    "GB": "🇬🇧 영국",
    "JP": "🇯🇵 일본",
    "DE": "🇩🇪 독일",
    "FR": "🇫🇷 프랑스",
    "CN": "🇨🇳 중국",
    "RU": "🇷🇺 러시아",
    "BR": "🇧🇷 브라질",
    "AU": "🇦🇺 호주",
    "CA": "🇨🇦 캐나다",
    "MX": "🇲🇽 멕시코",
    "SG": "🇸🇬 싱가포르",
    "TW": "🇹🇼 대만",
    "PL": "🇵🇱 폴란드",
    "TR": "🇹🇷 터키",
    "AR": "🇦🇷 아르헨티나",
    "IN": "🇮🇳 인도",
    "ID": "🇮🇩 인도네시아",
    "TH": "🇹🇭 태국",
}

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Steam API 호출 ──────────────────────────────────────────────────────────

def get_top_sellers(cc: str, page: int = 0, retries: int = 3) -> list[dict]:
    """Steam 국가별 Top Sellers 조회 (최대 100위)"""
    url = "https://store.steampowered.com/api/topsellers/"
    params = {
        "cc": cc,
        "l": "english",
        "page": page,
        "format": "json",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("top_sellers", {}).get("items", [])
            return items
        except Exception as e:
            log.warning(f"[{cc}] page={page} attempt={attempt+1} 실패: {e}")
            time.sleep(2 ** attempt)
    return []


def get_app_details(app_id: int, cc: str = "US") -> Optional[dict]:
    """특정 앱의 상세 정보 조회 (가격, 할인 등)"""
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": app_id, "cc": cc, "filters": "price_overview,basic_info"}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        app_data = data.get(str(app_id), {})
        if app_data.get("success"):
            return app_data.get("data", {})
    except Exception as e:
        log.warning(f"appdetails {app_id} [{cc}] 실패: {e}")
    return None


# ─── 데이터 파싱 ─────────────────────────────────────────────────────────────

def is_crimson_desert(item: dict) -> bool:
    """붉은사막 항목인지 확인"""
    name = item.get("name", "").lower()
    app_id = item.get("id", 0)
    if app_id == CRIMSON_DESERT_APP_ID:
        return True
    return any(cd in name for cd in CRIMSON_DESERT_NAMES)


def parse_item(item: dict, rank: int, cc: str) -> dict:
    """Top Sellers 아이템을 정규화된 dict로 변환"""
    original_price = item.get("original_price", 0) or 0
    final_price = item.get("final_price", 0) or 0
    discount_pct = item.get("discount_percent", 0) or 0
    is_free = item.get("is_free_game", False) or final_price == 0

    currency = item.get("currency", "USD")

    # 가격을 소수점 표시로 변환 (Steam API는 센트 단위)
    def fmt_price(cents: int) -> Optional[float]:
        if cents == 0:
            return None
        return round(cents / 100, 2)

    return {
        "rank": rank,
        "app_id": item.get("id"),
        "name": item.get("name", "Unknown"),
        "currency": currency,
        "original_price": fmt_price(original_price),
        "final_price": fmt_price(final_price) if not is_free else 0.0,
        "discount_percent": discount_pct,
        "is_free": is_free,
        "is_discounted": discount_pct > 0,
        "capsule_image": item.get("large_capsule_image", ""),
        "store_url": f"https://store.steampowered.com/app/{item.get('id', '')}",
        "cc": cc,
    }


def analyze_country(cc: str) -> dict:
    """한 국가의 Top Sellers를 분석하여 붉은사막 위치와 경쟁 게임 반환"""
    log.info(f"[{cc}] 분석 시작...")
    
    all_items = []
    # page 0, 1로 최대 ~100위까지 조회
    for page in range(2):
        items = get_top_sellers(cc, page=page)
        if not items:
            break
        all_items.extend(items)
        time.sleep(0.3)  # rate limit 방지

    if not all_items:
        log.warning(f"[{cc}] 데이터 없음")
        return {"cc": cc, "crimson_desert_rank": None, "rivals": [], "total_fetched": 0}

    # 붉은사막 위치 탐색
    crimson_rank = None
    for idx, item in enumerate(all_items):
        if is_crimson_desert(item):
            crimson_rank = idx + 1
            break

    # 붉은사막을 찾지 못한 경우: 전체를 rivals로 취급하지 않음
    if crimson_rank is None:
        log.info(f"[{cc}] 붉은사막 미발견 (Top {len(all_items)}위 내 없음)")
        return {
            "cc": cc,
            "crimson_desert_rank": None,
            "rivals": [],
            "total_fetched": len(all_items),
            "not_charted": True,
        }

    log.info(f"[{cc}] 붉은사막 순위: {crimson_rank}위")

    # 붉은사막보다 상위 중 무료/할인 게임 필터
    rivals = []
    for idx, item in enumerate(all_items[:crimson_rank - 1]):
        parsed = parse_item(item, idx + 1, cc)
        if parsed["is_free"] or parsed["is_discounted"]:
            rivals.append(parsed)

    log.info(f"[{cc}] 경쟁 게임(무료/할인): {len(rivals)}개")
    return {
        "cc": cc,
        "crimson_desert_rank": crimson_rank,
        "rivals": rivals,
        "total_fetched": len(all_items),
        "not_charted": False,
    }


# ─── 메인 실행 ───────────────────────────────────────────────────────────────

def run_tracker(countries: Optional[list] = None):
    """전체 국가 추적 실행"""
    if countries is None:
        countries = list(COUNTRIES.keys())

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = {
        "generated_at": timestamp,
        "crimson_desert_app_id": CRIMSON_DESERT_APP_ID,
        "countries": {},
    }

    for cc in countries:
        country_name = COUNTRIES.get(cc, cc)
        log.info(f"{'─'*50}")
        log.info(f"처리 중: {country_name} ({cc})")
        
        result = analyze_country(cc)
        results["countries"][cc] = {
            "name": country_name,
            **result,
        }
        time.sleep(0.5)  # 국가 간 딜레이

    # JSON 저장
    output_path = OUTPUT_DIR / "crimson_desert_rivals.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info(f"결과 저장: {output_path}")

    # 요약 출력
    print_summary(results)
    return results


def print_summary(results: dict):
    """콘솔 요약 출력"""
    print("\n" + "═" * 60)
    print("📊 붉은사막 경쟁 게임 추적 결과 요약")
    print(f"🕐 {results['generated_at']}")
    print("═" * 60)

    for cc, data in results["countries"].items():
        name = data.get("name", cc)
        rank = data.get("crimson_desert_rank")
        rivals = data.get("rivals", [])
        not_charted = data.get("not_charted", False)

        if not_charted:
            print(f"\n{name}: 순위권 밖")
            continue
        if rank is None:
            print(f"\n{name}: 데이터 없음")
            continue

        print(f"\n{name}: 붉은사막 {rank}위 | 상위 무료/할인 게임 {len(rivals)}개")
        for r in rivals[:5]:  # 상위 5개만 표시
            price_str = "FREE" if r["is_free"] else f"{r['currency']} {r['final_price']}"
            disc_str = f" (-{r['discount_percent']}%)" if r["discount_percent"] > 0 else ""
            print(f"  [{r['rank']}위] {r['name']} | {price_str}{disc_str}")

    print("\n" + "═" * 60)


if __name__ == "__main__":
    import sys

    # 커맨드라인으로 특정 국가만 지정 가능
    # 예: python crimson_desert_rival_tracker.py KR US JP
    target_countries = sys.argv[1:] if len(sys.argv) > 1 else None
    run_tracker(target_countries)
