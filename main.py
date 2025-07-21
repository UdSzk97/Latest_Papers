import feedparser
import requests
import openai
import os
import time

# === 設定 ===
# RSSフィード一覧（主要ジャーナル）
RSS_FEEDS = [
    "https://www.nature.com/nature.rss", # Nature
    "https://www.nature.com/natastron.rss", # Nature Astron.
    "https://www.nature.com/ngeo.rss", # Nature Geosci.
    "https://www.nature.com/ncomms.rss", # Nature Comm.
    "https://www.nature.com/srep.rss", # Scientific Reports
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science", # Science
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv", # Science Advances
    "https://api.crossref.org/works?filter=container-title:Icarus&sort=published&order=desc&rows=10", # Icarus
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9097", # JGR: Planets
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9402", # JGR: Space Physics
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1944-8007", # GRL
    "https://iopscience.iop.org/journal/1538-3873/rss", # PSJ
    "https://www.sciencedirect.com/journal/earth-and-planetary-science-letters/rss",
    "https://progearthplanetsci.springeropen.com/articles/rss.xml",
    "https://iopscience.iop.org/journal/0004-637X/rss", # ApJ
    "https://www.aanda.org/rss/latestArticles.xml", # A&A
    "https://academic.oup.com/rss/site_5326/3192.xml" # MNRAS
]

# キーワード設定
KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
    "asteroid", "comet", "exoplanet", "planet", "solar system", "kuiper belt"
]

# EXCLUDE_TERMS = [""]

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

posted_titles = set()

def contains_valid_keywords(text):
    text = text.lower()
    if any(term in text for term in EXCLUDE_TERMS):
        return False
    return any(keyword in text for keyword in KEYWORDS)

def post_to_slack(title, author, journal, link):
    # ¥n -> ¥n 変換（念のため）
    title_clean = title.replace("¥n", "\n").replace("¥¥n", "\n")
    message = f"*{title_clean}*¥n{author}, {journal}, <{link}|doi>"
    requests.post(SLACK_WEBHOOK_URL, json={"text": message})

def process_feed(feed_url):
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        if entry.title in posted_titles:
            continue

        full_text = (entry.title + " " + entry.get("summary", "")).lower()
        if not contains_valid_keywords(full_text):
            continue

        title = entry.title.strip()
        link = entry.link.strip()

        # デフォルト値（無い場合に備える）
        author = entry.get("author", "Unknown author")
        journal = entry.get("source", {}).get("title") or entry.get("dc_source") or "Unknown journal"

        print(f"通知: {title}")
        post_to_slack(title, author, journal, link)
        posted_titles.add(title)
        time.sleep(1)  # Slack API対策（OpenAI使ってないので緩く）

# === 実行 ===
if __name__ == "__main__":
    for feed_url in RSS_FEEDS:
        print(f"チェック中: {feed_url}")
        try:
            process_feed(feed_url)
        except Exception as e:
            print(f"エラー: {e}")
