import requests
from bs4 import BeautifulSoup
import os
from googletrans import Translator

DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
KEYWORDS = ['붉은사막', 'Crimson Desert', '펄어비스', 'Pearl Abyss']
LANG_SETTINGS = [
    ("ko", "KR", "KR:ko"),  # 한국어 뉴스
    ("en", "US", "US:en")   # 글로벌 영어 뉴스
]

translator = Translator()
sent_links = set()  # 중복 방지용

def fetch_news(keyword, lang, gl, ceid):
    url = f"https://news.google.com/rss/search?q={keyword}&hl={lang}&gl={gl}&ceid={ceid}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    return soup.find_all('item')[:5]

def check_news():
    for keyword in KEYWORDS:
        for lang, gl, ceid in LANG_SETTINGS:
            items = fetch_news(keyword, lang, gl, ceid)
            for item in items:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text
                description = item.description.text if item.description else ""

                if link in sent_links:
                    continue  # 이미 보낸 뉴스는 건너뛰기
                sent_links.add(link)

                # 번역 (영문일 경우만)
                if lang == "en":
                    title = translator.translate(title, src="en", dest="ko").text
                    description = translator.translate(description, src="en", dest="ko").text

                # 요약 메시지 구성
                message = f"📢 **[{keyword}] 새 소식**\n제목: {title}\n요약: {description[:150]}...\n링크: {link}"
                requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                break  # 최신 기사 하나만 보내기

if __name__ == "__main__":
    check_news()
