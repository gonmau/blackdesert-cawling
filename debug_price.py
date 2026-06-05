#!/usr/bin/env python3
import requests, json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# CS2(730), Marvel Rivals(2767030), Rainbow Six Siege(359550), Resident Evil Requiem(3764200)
TEST_APPS = {
    "730": "Counter-Strike 2 (F2P)",
    "2767030": "Marvel Rivals (F2P)",
    "359550": "Rainbow Six Siege (F2P)",
    "3764200": "Resident Evil Requiem (할인)",
}

for appid, name in TEST_APPS.items():
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us"
    res = requests.get(url, headers=HEADERS, timeout=10)
    data = res.json().get(appid, {}).get("data", {})
    print(f"\n{'='*50}")
    print(f"[{name}]")
    print(f"  type       : {data.get('type')}")
    print(f"  is_free    : {data.get('is_free')}")
    print(f"  price_overview: {data.get('price_overview')}")
