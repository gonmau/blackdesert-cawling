import requests
from bs4 import BeautifulSoup
import os
from googletrans import Translator
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
KEYWORDS = ['붉은사막', 'Crimson Desert', '펄어비스', 'Pearl Abyss']
LANG_SETTINGS = [
    ("en", "US", "US:en"),   # 미국
    ("zh-CN", "CN", "CN:zh-Hans"),  # 중국
    ("ja", "JP", "JP:ja")    # 일본
]

translator = Translator()
sent_links = set()

def fetch_news(keyword, lang, gl, ceid):
    url = f"https://news.google.com/rss/search?q={keyword}&hl={lang}&gl={gl}&ceid={ceid}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml-xml')
    return soup.find_all('item')[:5]

def check_news():
    today = datetime.now(timezone.utc).date()
    for keyword in KEYWORDS:
        for lang, gl, ceid in LANG_SETTINGS:
            items = fetch_news(keyword, lang, gl, ceid)
            for item in items:
                title = item.title.text
                link = item.link.text
                pub_date = parsedate_to_datetime(item.pubDate.text)

                if pub_date.date() != today:
                    continue
                if link in sent_links:
                    continue
                sent_links.add(link)

                description = item.description.text if item.description else ""

                # 번역 (영문/중문/일문 기사 → 한국어)
                if lang in ["en", "zh-CN", "ja"]:
                    title = translator.translate(title, dest="ko").text
                    description = translator.translate(description, dest="ko").text

                message = f"🌍 **[{keyword}] {gl} 최신 소식**\n제목: {title}\n요약: {description[:150]}...\n링크: {link}"
                requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                break

if __name__ == "__main__":
    check_news()
