#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SteamDB Global Top Sellers - 붉은사막 경쟁작 추적기 (실시간 매출 기준)
Playwright로 steamdb.info 스크래핑
"""
import json, time, re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ playwright 미설치: pip install playwright && playwright install chromium")
    sys.exit(1)

CRIMSON_DESERT_APPID = "3321460"
DATA_DIR = Path("data")
OUTPUT_FILE       = DATA_DIR / "steamdb_rivals.json"
HISTORY_FILE      = DATA_DIR / "steamdb_history.json"
RANK_HISTORY_FILE = DATA_DIR / "steamdb_rank_history.json"

STEAMDB_URL = "https://steamdb.info/stats/globaltopsellers/"
MAX_RANK_HISTORY = 180   # 6h × 180 = 45일


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
    """steamdb 순위 스크래핑 → [{rank, app_id, name, is_free, discount_pct}, ...]"""
    items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = ctx.new_page()

        print("  🌐 steamdb 페이지 로딩...")
        try:
            page.goto(STEAMDB_URL, wait_until="networkidle", timeout=45000)
        except Exception:
            page.goto(STEAMDB_URL, wait_until="domcontentloaded", timeout=45000)

        # 테이블 렌더링 대기 (JS로 채워짐)
        try:
            page.wait_for_selector("table.table-products tbody tr", timeout=20000)
        except Exception:
            # fallback: 그냥 기다리기
            time.sleep(8)

        rows = page.query_selector_all("table.table-products tbody tr")
        if not rows:
            # selector 변경 대응
            rows = page.query_selector_all("tbody tr")

        print(f"  📋 {len(rows)}행 발견")

        for row in rows:
            try:
                # 순위
                rank_el = row.query_selector("td:nth-child(1)")
                rank_txt = rank_el.inner_text().strip().rstrip('.') if rank_el else ""
                if not rank_txt.isdigit():
                    continue
                rank = int(rank_txt)

                # 게임명 + appid
                link_el = row.query_selector("a[href*='/app/']")
                if not link_el:
                    continue
                name = link_el.inner_text().strip()
                href = link_el.get_attribute("href") or ""
                m = re.search(r"/app/(\d+)/", href)
                if not m:
                    continue
                appid = m.group(1)

                # 할인율
                disc_el = row.query_selector("[data-discount], .discount, td:nth-child(4)")
                discount_pct = 0
                is_free = False

                price_el = row.query_selector("td[data-price], .td-price")
                if price_el:
                    price_txt = price_el.inner_text().strip().lower()
                    if price_txt in ("free", "free to play", ""):
                        is_free = True
                    else:
                        disc_match = re.search(r"-(\d+)%", price_txt)
                        if disc_match:
                            discount_pct = int(disc_match.group(1))

                items.append({
                    "app_id": appid,
                    "name": name,
                    "rank": rank,
                    "is_free": is_free,
                    "is_discounted": discount_pct > 0 and not is_free,
                    "discount_pct": discount_pct,
                })

            except Exception:
                continue

        browser.close()

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
        # 실패해도 기존 데이터 유지 (파일 덮어쓰지 않음)
        return

    if not raw_items:
        print("❌ 데이터 없음 (Cloudflare 차단 또는 구조 변경 가능성)")
        return

    print(f"✅ {len(raw_items)}개 게임 수집")

    # 붉은사막 찾기
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

        # 붉은사막 앞에서 무료/할인만
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
