import requests
from bs4 import BeautifulSoup
import os
from newspaper import Article
from googletrans import Translator
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
KEYWORDS = ['붉은사막', 'Crimson Desert', '펄어비스', 'Pearl Abyss']
RSS_FEEDS = [
    "https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q={keyword}&hl=en&gl=US&ceid=US:en",
    "https://www.ign.com/rss.xml",
    "https://www.gamespot.com/feeds/news/"
]

translator = Translator()
sent_links = set()

def fetch_rss(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml-xml')
    return soup.find_all('item')[:5]

def summarize_article(link):
    try:
        article = Article(link)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except:
        return ""

def check_news():
    today = datetime.now(timezone.utc).date()
    for keyword in KEYWORDS:
        for feed in RSS_FEEDS:
            url = feed.format(keyword=keyword)
            items = fetch_rss(url)
            for item in items:
                title = item.title.text
                link = item.link.text
                pub_date = parsedate_to_datetime(item.pubDate.text)
                
                if pub_date.date() != today:
                    continue
                if link in sent_links:
                    continue
                sent_links.add(link)

                summary = summarize_article(link)
                if not summary:
                    summary = item.description.text if item.description else ""

                # 번역 (영문 기사일 경우)
                if any(c.isalpha() for c in title):  # 영어 포함 여부 체크
                    summary = translator.translate(summary, src="en", dest="ko").text
                    title = translator.translate(title, src="en", dest="ko").text

                message = f"📢 **[{keyword}] 새 소식**\n제목: {title}\n요약: {summary}\n링크: {link}"
                requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                break

if __name__ == "__main__":
    check_news()
