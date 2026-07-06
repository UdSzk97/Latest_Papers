import feedparser
import requests
import os
import time

# === 設定 ===
RSS_FEEDS = {
    "https://www.annualreviews.org/rss/content/journals/astro/latestarticles?fmt=rss": "Annual Review of A&A", 
    "http://www.aanda.org/articles/aa/rss/TOCRSS/rss.xml": "A&A", 
    "https://iopscience.iop.org/journal/rss/1538-3881": "AJ", 
    "https://iopscience.iop.org/journal/rss/0004-637X": "ApJ",
    "https://link.springer.com/search.rss?facet-journal-id=11352": "ASR", 
    "https://rss.sciencedirect.com/publication/science/00092541": "Chemical Geology", 
    "https://earth-planets-space.springeropen.com/articles/most-recent/rss.xml": "EPS", 
    "https://rss.sciencedirect.com/publication/science/0012821X": "EPSL", 
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9097": "JGR: Planets", 
    "https://agupubs.onlinelibrary.wiley.com/action/showFeed?jc=21699100&type=etoc&feed=rss": "JGR: Planets", # updated on Jul. 6, 2026
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)2169-9402": "JGR: Space Physics", 
    "https://agupubs.onlinelibrary.wiley.com/action/showFeed?jc=21699402&type=etoc&feed=rss": "JGR: Space Physics", # updated on Jul. 6, 2026
    "https://rss.sciencedirect.com/publication/science/00167037": "GCA", 
    "https://agupubs.onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1944-8007": "GRL", 
    "https://rss.sciencedirect.com/publication/science/00191035": "Icarus", 
    "https://onlinelibrary.wiley.com/feed/19455100/most-recent": "MaPS", 
    "https://academic.oup.com/rss/site_5326/3192.xml": "MNRAS", 
    "https://www.nature.com/nature.rss": "Nature", 
    "https://www.nature.com/natastron.rss": "Nat. Astron.", 
    "https://www.nature.com/ncomms.rss": "Nat. Comm.", 
    "https://www.nature.com/ngeo.rss": "Nat. Geosci.", 
    "https://progearthplanetsci.springeropen.com/articles/most-recent/rss.xml": "PEPS", 
    "https://www.pnas.org/rss/current.xml": "PNAS", 
    "https://iopscience.iop.org/journal/rss/2632-3338": "PSJ", 
    "https://rss.sciencedirect.com/publication/science/00320633": "PSS", 
    "https://www.mdpi.com/rss/journal/remotesensing": "Remote Sensing", 
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science": "Science", 
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv": "Sci. Adv.", 
    "https://www.nature.com/srep.rss": "Sci. Rep.", 
    "https://feeds.feedburner.com/edp_swsc?format=xml": "SWSC", 
    "https://link.springer.com/search.rss?facet-journal-id=11214": "SSR"
}

KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "moon", 
    "phobos", "deimos", " io ", " europa ", "ganymede", "calisto", "enceladus", "pluto",  
    "dwarf planet", "asteroid", "comet", "meteoroid", "meteorite", "habitable", "habitability", "exoplanet", "crater", 
    "hermean", "martian", "jovian", "lunar", "meteoritic"
] # "planet", "solar system",  "kuiper belt", "eris", "ceres", "makemake", "haumea", 

# 変換用マッピング（左側がヒットした単語、右側がハッシュタグにする代表語）
TAG_MAPPING = {
    "meteoritic": "meteorite",
    "martian": "mars",
    "hermean": "mercury",
    "jovian": "jupiter",
    "lunar": "moon"
}

"""
KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "moon", 
    "phobos", "deimos", " io ", " europa ", "ganymede", "calisto", "enceladus", 
    " dwarf planet ", "asteroid", "comet", "meteoroid", "meteorite", "habitable", "habitability", "exoplanet", "crater", 
    "mercury's", "hermean", "venusian", "martian", "jovian", "lunar", "cometary", "meteoritic", 
    "moons", "asteroids", "comets", "meteorites", "exoplanets", "craters"
] # "planet", "solar system",  "kuiper belt", "pluto", "eris", "ceres", "makemake", "haumea", 
"""

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
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

def get_first_author(entry):
    raw_author = ""
    
    # 1. 標準の author プロパティをチェック
    if hasattr(entry, "author") and entry.author:
        raw_author = entry.author
    # 2. dc:creator (feedparserが拡張メタデータとして拾う場合がある) をチェック
    elif "dc_creator" in entry:
        raw_author = entry.dc_creator
    # 3. authors リストの最初の要素をチェック
    elif "authors" in entry and entry.authors:
        raw_author = entry.authors[0].get("name", "")

    raw_author = raw_author.strip()
    if not raw_author:
        return "Unknown Author"

    # ファーストオーサーのみを抽出（カンマや and で分割）
    if "," in raw_author:
        first_author = raw_author.split(",")[0].strip()
    elif " and " in raw_author:
        first_author = raw_author.split(" and ")[0].strip()
    else:
        first_author = raw_author

    return first_author

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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    # ループを辞書のキーと値（URLとジャーナル名）で回す
    for feed_url, journal_name in RSS_FEEDS.items():
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"RSS読み込みエラー: {feed_url} : {e}")
            continue

        # journal = feed.feed.get("title", "Unknown journal") # ←自動取得はナシ

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            abstract_text = entry.get("summary", "")
            
            # <dc:description> の取得
            if "dc_description" in entry:
                abstract_text += " " + entry.dc_description
                
            # <content:encoded> などの取得
            if "content" in entry:
                for content_item in entry.content:
                    abstract_text += " " + content_item.get("value", "")

            abstract_text = abstract_text.strip()
            summary = entry.get("summary", "").strip()
            link = entry.get("link", "")

            if not title or title in posted_titles:
                continue

            # タイトルと結合したアブストラクトを検査対象にする
            text_to_check = title + " " + abstract_text + " " + summary
            # if contains_keywords(text_to_check):
            matched = matched_keywords(text_to_check)
            if matched:
                normalized_tags = set()
                for k in matched:
                    base_word = TAG_MAPPING.get(k, k)
                    normalized_tags.add(base_word)
                    
                tags = " ".join(f"#{word.capitalize()}" for word in normalized_tags)
                
                # 安全な著者名取得関数を呼び出す
                first_author = get_first_author(entry)

                # --- Slackメッセージの組み立て（ご提案の形式） ---
                # <URL|テキスト> の形式にすることで、タイトル全体が青文字リンクになります
                message = f"<{link}|*{title}*>\n{first_author} | {journal_name} | {tags}"
                
                print("Posting to Slack:\n", message)
                post_to_slack(message)
                save_posted_title(title)
                time.sleep(1) # Slack制限対策

if __name__ == "__main__":
    main()
