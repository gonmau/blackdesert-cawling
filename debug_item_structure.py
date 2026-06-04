#!/usr/bin/env python3
"""
debug_item_structure.py
실제 Steam search/results JSON item 구조 확인용
→ data/debug_item_kr.json 에 저장 후 종료
GitHub Actions에서 한 번만 실행하면 됨
"""
import json, re, time, requests
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

Path("data").mkdir(exist_ok=True)

for cc in ["kr", "us"]:
    print(f"[{cc}] 요청 중...", flush=True)
    r = requests.get(
        "https://store.steampowered.com/search/results/",
        params={"filter": "topsellers", "cc": cc, "l": "en", "json": 1, "page": 1},
        headers=HEADERS, timeout=20,
    )
    print(f"[{cc}] status: {r.status_code}", flush=True)
    if r.status_code != 200:
        print(r.text[:200])
        continue

    data  = r.json()
    items = data.get("items", [])
    print(f"[{cc}] items: {len(items)}개", flush=True)

    # 첫 5개 아이템 전체 키·값 출력
    for i, item in enumerate(items[:5]):
        print(f"\n--- [{cc}] item[{i}] ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    # 파일로도 저장
    out = f"data/debug_item_{cc}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"top_keys": list(data.keys()), "items": items[:5]}, f,
                  ensure_ascii=False, indent=2)
    print(f"\n✅ 저장: {out}", flush=True)
    time.sleep(2)
