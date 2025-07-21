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
    "https://iopscience.iop.org/journal/rss/2632-3338", # PSJ
    "https://rss.sciencedirect.com/publication/science/0012821X", # EPSL
    "https://progearthplanetsci.springeropen.com/articles/most-recent/rss.xml", # PEPS
    "https://earth-planets-space.springeropen.com/articles/most-recent/rss.xml", # EPS
    "https://iopscience.iop.org/journal/rss/0004-637X", # ApJ
    "https://iopscience.iop.org/journal/rss/1538-3881", # AJ
    "http://www.aanda.org/articles/aa/rss/TOCRSS/rss.xml", # A&A
    "https://academic.oup.com/rss/site_5326/3192.xml" # MNRAS
]

KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
    "asteroid", "comet", "exoplanet", "planet", "solar system", "kuiper belt"
]

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

posted_titles = set()

def contains_valid_keywords(text):
    text = text.lower()
    return any(keyword in text for keyword in KEYWORDS) # return True

def extract_first_author(author_str):
    # 著者名が複数の場合を考慮し、最初の著者のみ抽出
    if not author_str:
        return "Unknown author"
    # 例えば "John Doe, Jane Smith and Someone Else" の場合
    # カンマまたは " and " で区切る
    sep_candidates = [",", " and "]
    for sep in sep_candidates:
        if sep in author_str:
            return author_str.split(sep)[0].strip()
    return author_str.strip()

def extract_journal(entry):
    # いろんな場所からジャーナル名を探す
    journal = (
        entry.get("source", {}).get("title") or
        entry.get("dc_source") or
        entry.get("journal") or
        entry.get("publisher") or
        entry.get("container_title") or
        None
    )
    if journal:
        return journal
    else:
        return "Unknown journal"

def post_to_slack(title, author, journal, link):
    title_clean = title.replace("¥n", "\n").replace("¥¥n", "\n")
    message = f"*{title_clean}*\n{author}, {journal}, {link}"
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    if response.status_code != 200:
        print(f"Slack送信失敗: {response.status_code} {response.text}")

# === メイン処理 ===
if __name__ == "__main__":
    for url in RSS_FEEDS:
        try:
            process_feed(url)
        except Exception as e:
            print(f"エラー (URL: {url}): {e}")
