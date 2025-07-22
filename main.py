import requests
import datetime
import os
import time

# === 設定 ===
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
    "asteroid", "comet", "exoplanet", "planet", "solar system", "kuiper belt"
]
CROSSREF_API = "https://api.crossref.org/works"
DATE_FROM = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
ROWS = 30

# === Slack通知関数 ===
def post_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print("Slack送信エラー:", response.text)

# === CrossRef検索＆処理 ===
def search_and_notify():
    for keyword in KEYWORDS:
        print(f"¥CID{1821} Searching keyword: {keyword}")
        params = {
            "query": keyword,
            "filter": f"from-pub-date:{DATE_FROM}",
            "sort": "published",
            "order": "desc",
            "rows": ROWS,
        }
        try:
            res = requests.get(CROSSREF_API, params=params)
            res.raise_for_status()
            items = res.json().get("message", {}).get("items", [])
        except Exception as e:
            print(f"CrossRef API error for '{keyword}': {e}")
            continue

        for item in items:
            title = item.get("title", [""])[0]
            doi = item.get("DOI", "")
            url = f"https://doi.org/{doi}"

            # タイトルにキーワードが含まれているか再チェック
            if not any(k.lower() in title.lower() for k in KEYWORDS):
                continue

            # 著者とジャーナル名取得
            authors = item.get("author", [])
            first_author = f"{authors[0].get('family', '')} et al." if authors else "Unknown author"
            journal = item.get("container-title", [""])[0] or "Unknown journal"

            # Slack投稿メッセージ作成
            message = f"{title}\n{first_author}, {journal}, {url}"
            print("Posting to Slack:\n", message)
            post_to_slack(message)

            time.sleep(1)

if __name__ == "__main__":
    search_and_notify()
