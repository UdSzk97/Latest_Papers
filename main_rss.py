import feedparser
import requests
import os
import time

# === 設定 ===
RSS_FEEDS = [
    "http://www.aanda.org/articles/aa/rss/TOCRSS/rss.xml", # A&A
    "https://iopscience.iop.org/journal/rss/1538-3881", # AJ
    "https://iopscience.iop.org/journal/rss/0004-637X", # ApJ
    "https://link.springer.com/search.rss?facet-journal-id=11352", # ASR
    "https://rss.sciencedirect.com/publication/science/00092541", # CG (Chemical Geology)
    "https://earth-planets-space.springeropen.com/articles/most-recent/rss.xml", # EPS
    "https://rss.sciencedirect.com/publication/science/0012821X", # EPSL
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9097", # JGR: Planets
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9402", # JGR: Space Physics
    "https://rss.sciencedirect.com/publication/science/00167037", # GCA
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1944-8007", # GRL
    "https://api.crossref.org/works?filter=container-title:Icarus&sort=published&order=desc&rows=10", # Icarus
    "https://onlinelibrary.wiley.com/feed/19455100/most-recent" # MaPS
    "https://academic.oup.com/rss/site_5326/3192.xml", # MNRAS
    "https://www.nature.com/nature.rss", # Nature
    "https://www.nature.com/natastron.rss", # Nature Astron.
    "https://www.nature.com/ncomms.rss", # Nature Comm.
    "https://www.nature.com/ngeo.rss", # Nature Geosci.
    "https://progearthplanetsci.springeropen.com/articles/most-recent/rss.xml", # PEPS
    "https://www.pnas.org/rss/current.xml", # PNAS
    "https://iopscience.iop.org/journal/rss/2632-3338", # PSJ
    "https://rss.sciencedirect.com/publication/science/00320633", # PSS
    "https://www.mdpi.com/rss/journal/remotesensing", # RS (Remote Sensing)
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science", # Science
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv", # Science Advances
    "https://www.nature.com/srep.rss", # Scientific Reports
    "https://feeds.feedburner.com/edp_swsc?format=xml", # SWSC
    "https://link.springer.com/search.rss?facet-journal-id=11214" # SSR
]

KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "moon", 
    "hermean", "venusian", "martian", "jovian", "lunar", 
    "dwarf planet", "asteroid", "comet", "meteorite", "habitable", "habitability", "exoplanet"
] # "planet", "solar system",  "kuiper belt", "pluto", "eris", "ceres", "makemake", "haumea", 

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL_UsuiLab")
POSTED_TITLES_FILE = "posted_titles.txt"

# === ユーティリティ関数 ===
def load_posted_titles():
    if os.path.exists(POSTED_TITLES_FILE):
        with open(POSTED_TITLES_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def save_posted_title(title):
    with open(POSTED_TITLES_FILE, "a", encoding="utf-8") as f:
        f.write(title + "\n")

def contains_keywords(text):
    text = text.lower()
    return any(keyword in text for keyword in KEYWORDS)

def matched_keywords(text):
    text = text.lower()
    matched = [keyword for keyword in KEYWORDS if keyword in text]
    return matched

def post_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print(f"Slack送信失敗: {response.status_code} {response.text}")

# === メイン処理 ===
def main():
    posted_titles = load_posted_titles()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"RSS読み込みエラー: {feed_url} : {e}")
            continue

        journal = feed.feed.get("title", "Unknown journal")

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            link = entry.get("link", "")

            if not title or title in posted_titles:
                continue

            text_to_check = title + " " + summary
            # if contains_keywords(text_to_check):
            matched = matched_keywords(text_to_check)
            if matched:
                # タグの生成（例: "#Mercury #Comet"）
                tags = " ".join(f"#{k.capitalize()}" for k in matched)

                # 著者名から first author を抽出
                if hasattr(entry, "author") and entry.author:
                    raw_author = entry.author.strip()
                    if "," in raw_author:
                        first_author = raw_author.split(",")[0].strip()
                    elif " and " in raw_author:
                        first_author = raw_author.split(" and ")[0].strip()
                    else:
                        first_author = raw_author
                else:
                    first_author = "Unknown author"

                # author = entry.get("author", "Unknown author")
                message = f"{title}\n{link}\n{tags}"
                # message = f"{title}\n{first_author}, {journal}, {link}"
                print("Posting to Slack:\n", message)
                post_to_slack(message)
                save_posted_title(title)
                time.sleep(1)  # Slack制限対策

if __name__ == "__main__":
    main()
