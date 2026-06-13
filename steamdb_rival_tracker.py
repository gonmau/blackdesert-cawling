#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SteamDB Global Top Sellers - 붉은사막 경쟁작 추적기 (실시간 매출 기준)
undetected-chromedriver로 steamdb.info 스크래핑 (로컬 PC 전용)
"""
import json, time, re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("❌ 미설치: pip install undetected-chromedriver selenium")
    sys.exit(1)

CRIMSON_DESERT_APPID = "3321460"
DATA_DIR = Path("data")
OUTPUT_FILE       = DATA_DIR / "steamdb_rivals.json"
HISTORY_FILE      = DATA_DIR / "steamdb_history.json"
RANK_HISTORY_FILE = DATA_DIR / "steamdb_rank_history.json"

STEAMDB_URL = "https://steamdb.info/stats/globaltopsellers/"
MAX_RANK_HISTORY = 180


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


def scrape_steamdb():
    options = uc.ChromeOptions()
    # headless 대신 화면 밖으로 밀어서 백그라운드처럼 실행
    options.add_argument("--window-position=-2000,0")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options)
    items = []

    try:
        print("  🌐 steamdb 페이지 로딩...")
        driver.get(STEAMDB_URL)

        # 테이블 링크 대기 (최대 30초)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/app/']"))
        )
        time.sleep(2)  # 추가 렌더링 여유

        rows = driver.find_elements(By.CSS_SELECTOR, "tr")
        print(f"  📋 {len(rows)}행 발견")

        for row in rows:
            try:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if not cells:
                    continue

                # 순위
                rank_txt = cells[0].text.strip().rstrip('.')
                if not rank_txt.isdigit():
                    continue
                rank = int(rank_txt)

                # 게임명 + appid
                link_el = row.find_element(By.CSS_SELECTOR, "a[href*='/app/']")
                # td[2]에 게임명, 링크 text는 첫번째가 빈 이미지링크라 td 사용
                name = cells[2].text.strip() if len(cells) > 2 else link_el.text.strip()
                href = link_el.get_attribute("href") or ""
                m = re.search(r"/app/(\d+)/", href)
                if not m:
                    continue
                appid = m.group(1)

                # 가격/할인: 행 전체 텍스트에서 추출
                row_text = row.text
                is_free = bool(re.search(r'\bfree\b', row_text, re.IGNORECASE))
                disc_match = re.search(r'-(\d+)%', row_text)
                discount_pct = int(disc_match.group(1)) if disc_match and not is_free else 0

                items.append({
                    "app_id": appid,
                    "name": name,
                    "rank": rank,
                    "is_free": is_free,
                    "is_discounted": discount_pct > 0,
                    "discount_pct": discount_pct,
                })

            except Exception:
                continue

    except Exception as e:
        print(f"  ❌ 스크래핑 오류: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    items.sort(key=lambda x: x["rank"])
    return items


def run():
    DATA_DIR.mkdir(exist_ok=True)
    history = get_history()
    rank_history = get_rank_history()
    now_str = datetime.now(timezone(timedelta(hours=9))).isoformat()

    print("🔍 SteamDB Global Top Sellers 수집 중...")

    try:
        raw_items = scrape_steamdb()
    except Exception as e:
        print(f"❌ 스크래핑 실패: {e}")
        return

    if not raw_items:
        print("❌ 데이터 없음")
        return

    print(f"✅ {len(raw_items)}개 게임 수집")

    crimson_item = next((i for i in raw_items if i["app_id"] == CRIMSON_DESERT_APPID), None)

    if crimson_item is None:
        print("⚠️  100위 안에 붉은사막 없음")
        output = {"generated_at": now_str, "crimson_desert_rank": None, "rank_diff": 0, "rivals": []}
    else:
        crimson_rank = crimson_item["rank"]
        prev_rank = history.get(CRIMSON_DESERT_APPID, crimson_rank)
        rank_diff = prev_rank - crimson_rank
        diff_str = (f" (▲{rank_diff})" if rank_diff > 0
                    else f" (▼{abs(rank_diff)})" if rank_diff < 0 else "")
        print(f"✅ 붉은사막 SteamDB {crimson_rank}위{diff_str}")

        rivals = []
        for item in raw_items:
            if item["rank"] >= crimson_rank:
                break
            if item["is_free"] or item["is_discounted"]:
                prev_r = history.get(item["app_id"], item["rank"])
                item["rank_diff"] = prev_r - item["rank"]
                rivals.append(item)

        print(f"📊 경쟁작(무료/할인): {len(rivals)}개")

        rank_history.append({"t": now_str, "rank": crimson_rank})
        if len(rank_history) > MAX_RANK_HISTORY:
            rank_history = rank_history[-MAX_RANK_HISTORY:]

        output = {
            "generated_at": now_str,
            "crimson_desert_rank": crimson_rank,
            "rank_diff": rank_diff,
            "rivals": rivals,
        }

    new_history = {item["app_id"]: item["rank"] for item in raw_items}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
    with open(RANK_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(rank_history, f, ensure_ascii=False, indent=2)

    print(f"💾 저장 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
