import requests
from bs4 import BeautifulSoup
import os

# GitHub Secrets에서 환경변수 가져오기
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
KEYWORDS = ['붉은사막', 'Crimson Desert', '펄어비스', 'Pearl Abyss']

def check_news():
    for keyword in KEYWORDS:
        # 구글 뉴스 RSS 피드 URL (한글/한국 설정)
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'xml') # XML 파싱
        
        items = soup.find_all('item')[:5] # 최신 뉴스 5개만 확인
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date = item.pubDate.text
            
            # 메시지 구성 및 전송
            message = f"📢 **[{keyword}] 새 소식**\n제목: {title}\n링크: {link}"
            requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
            break # 중복 방지를 위해 가장 최신 것 하나만 보내도록 설정 (로직 수정 가능)

if __name__ == "__main__":
    check_news()
