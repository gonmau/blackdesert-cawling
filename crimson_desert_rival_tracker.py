"""
crimson_desert_rival_tracker.py
붉은사막(Crimson Desert)보다 상위 순위의 무료/할인 게임 추적기
store.steampowered.com/search/results/ API 사용 (기존 steam_topseller_tracker.py 방식)
"""

import requests
import json
import time
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

# ─── 설정 ────────────────────────────────────────────────────────────────────

STEAM_APP_IDS = {"1143720"}  # Crimson Desert

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

TARGET_COUNTRIES = {
    "us": "🇺🇸 미국",
    "gb": "🇬🇧 영국",
    "de": "🇩🇪 독일",
    "fr": "🇫🇷 프랑스",
    "ca": "🇨🇦 캐나다",
    "br": "🇧🇷 브라질",
    "jp": "🇯🇵 일본",
    "kr": "🇰🇷 한국",
    "cn": "🇨🇳 중국",
    "ru": "🇷🇺 러시아",
    "au": "🇦🇺 호주",
    "es": "🇪🇸 스페인",
    "it": "🇮🇹 이탈리아",
    "pl": "🇵🇱 폴란드",
    "tr": "🇹🇷 터키",
    "nl": "🇳🇱 네덜란드",
    "se": "🇸🇪 스웨덴",
    "no": "🇳🇴 노르웨이",
    "dk": "🇩🇰 덴마크",
    "fi": "🇫🇮 핀란드",
    "at": "🇦🇹 오스트리아",
    "ch": "🇨🇭 스위스",
    "cz": "🇨🇿 체코",
    "sg": "🇸🇬 싱가포르",
    "be": "🇧🇪 벨기에",
    "hk": "🇭🇰 홍콩",
    "nz": "🇳🇿 뉴질랜드",
    "tw": "🇹🇼 대만",
    "th": "🇹🇭 태국",
}

# 국가별 재시도 딜레이 (초). 느린 국가는 따로 지정
DEFAULT_RETRY_DELAYS = [2, 5, 10]
RETRY_DELAYS = {
    "cn": [3, 8, 15],
    "ru": [3, 8, 15],
    "tr": [3, 8, 15],
}

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Steam search/results API (기존 방식) ────────────────────────────────────

def fetch_page(cc: str, page: int, retry_delays: list) -> dict | None:
    """Steam search/results API 한 페이지 호출"""
    url = "https://store.steampowered.com/search/results/"
    params = {
        "filter": "topsellers",
        "cc": cc,
        "l": "en",
        "json": 1,
        "page": page,
    }
    for attempt, delay in enumerate([0] + retry_delays):
        if delay > 0:
            log.info(f"  ⏳ [{cc}] p{page} {delay}초 후 재시도 ({attempt}/{len(retry_delays)})...")
            time.sleep(delay)
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                log.warning(f"  ⚠️ [{cc}] p{page} 429 Rate Limited")
                if attempt == len(retry_delays):
                    log.error(f"  ❌ [{cc}] p{page} 재시도 초과")
                    return None
                continue
            else:
                log.warning(f"  ⚠️ [{cc}] p{page} 응답 실패: {r.status_code}")
                return None
        except Exception as e:
            log.error(f"  ❌ [{cc}] p{page} 오류: {e}")
            return None
    return None


def parse_item_html(item: dict) -> dict | None:
    """
    search/results JSON 아이템에서 appid, 이름, 가격 정보 파싱
    item 구조 예시:
      {
        "name": "Game Title",
        "logo": "https://...steam/apps/12345/...",
        "price": "₩ 59,800",           # 정가 (할인 중이면 취소선 원본)
        "discounted_price": "₩ 29,900", # 할인가 (없으면 None)
        "discount_percent": "-50%",      # 없으면 ""
        "app_name": "...",
        "metascore": ...,
        "type": "app"|"bundle"|...
      }
    실제 필드명은 Steam 응답에 따라 다를 수 있으므로 방어적으로 파싱
    """
    logo = item.get("logo", "")
    m = re.search(r"/steam/apps/(\d+)/", logo)
    if not m:
        return None
    appid = m.group(1)

    name = item.get("name", "") or item.get("app_name", "") or "Unknown"

    # 가격 파싱: Steam은 국가별로 통화 기호가 다름
    # price 필드: 정가 (문자열), discounted_price: 할인가 (문자열 or None)
    raw_price = item.get("price", "") or ""
    raw_disc  = item.get("discounted_price") or ""
    disc_pct_str = item.get("discount_percent", "") or ""

    # "Free to Play" / "Free" 감지
    is_free = any(kw in raw_price.lower() for kw in ["free", "무료"])

    # 할인율 숫자 추출 ("-50%" → 50)
    disc_pct = 0
    pct_match = re.search(r"(\d+)", disc_pct_str)
    if pct_match:
        disc_pct = int(pct_match.group(1))

    is_discounted = disc_pct > 0 or (bool(raw_disc) and raw_disc != raw_price)

    return {
        "app_id": appid,
        "name": name,
        "original_price": raw_price.strip() if not is_free else None,
        "final_price": raw_disc.strip() if (is_discounted and raw_disc) else (raw_price.strip() if not is_free else "Free"),
        "discount_percent": disc_pct,
        "is_free": is_free,
        "is_discounted": is_discounted,
        "store_url": f"https://store.steampowered.com/app/{appid}",
    }


def analyze_country(cc: str) -> dict:
    """한 국가 전체를 스캔: 붉은사막 위치 탐색 + 상위 무료/할인 게임 수집"""
    retry_delays = RETRY_DELAYS.get(cc, DEFAULT_RETRY_DELAYS)
    seen_ids: set[str] = set()
    real_rank = 0
    crimson_rank = None
    rivals: list[dict] = []      # 붉은사막 상위의 무료/할인 게임
    candidates: list[dict] = []  # 붉은사막 발견 전 누적

    for page in range(1, 11):  # 최대 10페이지 = 약 250위
        data = fetch_page(cc, page, retry_delays)
        if data is None:
            break
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            parsed = parse_item_html(item)
            if parsed is None:
                continue
            appid = parsed["app_id"]
            if appid in seen_ids:
                continue
            seen_ids.add(appid)
            real_rank += 1
            parsed["rank"] = real_rank
            parsed["cc"] = cc

            if appid in STEAM_APP_IDS:
                crimson_rank = real_rank
                # 지금까지 모은 candidates 중 무료/할인만 rivals로 확정
                rivals = [c for c in candidates if c["is_free"] or c["is_discounted"]]
                break  # 붉은사막 발견 → 이 국가 완료

            candidates.append(parsed)

        if crimson_rank is not None:
            break

        time.sleep(1.0)  # 페이지 간 딜레이

    if real_rank == 0:
        log.warning(f"  ⚠️ [{cc}] 데이터 없음")
        return {"cc": cc, "crimson_desert_rank": None, "rivals": [], "total_fetched": 0, "error": True}

    status = f"#{crimson_rank}" if crimson_rank else "순위권 밖"
    log.info(f"  ✅ [{cc}] 총 {real_rank}개 파싱 | 붉은사막 {status} | 경쟁 {len(rivals)}개")

    return {
        "cc": cc,
        "crimson_desert_rank": crimson_rank,
        "rivals": rivals,
        "total_fetched": real_rank,
        "not_charted": crimson_rank is None,
        "error": False,
    }


# ─── 메인 실행 ───────────────────────────────────────────────────────────────

def run_tracker(countries: list[str] | None = None):
    if countries is None:
        countries = list(TARGET_COUNTRIES.keys())

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = {
        "generated_at": timestamp,
        "crimson_desert_app_id": list(STEAM_APP_IDS)[0],
        "countries": {},
    }

    for cc in countries:
        country_name = TARGET_COUNTRIES.get(cc, cc.upper())
        log.info("─" * 50)
        log.info(f"처리 중: {country_name} ({cc})")

        result = analyze_country(cc)
        results["countries"][cc] = {"name": country_name, **result}
        time.sleep(0.8)

    # 저장
    out = OUTPUT_DIR / "crimson_desert_rivals.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info(f"💾 저장 완료: {out}")

    # 요약
    charted = [v for v in results["countries"].values()
               if not v.get("not_charted") and v.get("crimson_desert_rank")]
    log.info("=" * 50)
    log.info(f"순위권 국가: {len(charted)}개 / 전체 {len(countries)}개")
    for cc, d in results["countries"].items():
        r = d.get("crimson_desert_rank")
        rv = len(d.get("rivals", []))
        tag = f"#{r} (경쟁 {rv}개)" if r else ("순위권 밖" if not d.get("error") else "오류")
        log.info(f"  {d['name']}: {tag}")

    return results


if __name__ == "__main__":
    import sys
    target = [c.lower() for c in sys.argv[1:]] if len(sys.argv) > 1 else None
    run_tracker(target)
