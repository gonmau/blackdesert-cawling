import requests, json

url = "https://store.steampowered.com/search/results/?query&start=0&count=10&filter=topsellers&cc=us&json=1"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
res = requests.get(url, headers=headers)
print("status:", res.status_code)
data = res.json()
print("keys:", list(data.keys()))
print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
