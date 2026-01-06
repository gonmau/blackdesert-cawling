import os
import subprocess
import json
import requests
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
KEYWORDS = ["붉은사막", "Crimson Desert", "펄어비스", "Pearl Abyss"]

def fetch_tweets(keyword):
    today = datetime.now().strftime("%Y-%m-%d")
    cmd = f"snscrape --jsonl --max-results 5 twitter-search '{keyword} since:{today}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    tweets = []
    for line in result.stdout.splitlines():
        data = json.loads(line)
        tweets.append({
            "user": data["user"]["username"],
            "content": data["content"],
            "link": data["url"]
        })
    return tweets

def send_to_discord(keyword, tweets):
    for t in tweets:
        message = f"🐦 **[{keyword}] 트윗 소식**\n작성자: @{t['user']}\n내용: {t['content']}\n링크: {t['link']}"
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

def main():
    for keyword in KEYWORDS:
        tweets = fetch_tweets(keyword)
        if tweets:
            send_to_discord(keyword, tweets)

if __name__ == "__main__":
    main()
