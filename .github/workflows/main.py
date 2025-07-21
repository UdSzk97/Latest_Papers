import requests
import datetime
import os
import openai
import time

# === 設定 ===
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"  # あなたのSlack Webhook
KEYWORDS = [
    "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
    "asteroid", "comet", "exoplanet", "planet", "solar system", "kuiper belt"
]
CROSSREF_API = "https://api.crossref.org/works"
DATE_FROM = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
ROWS = 30

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key is None:
    raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。")

# === 翻訳関数 ===
def translate_text_en_to_ja(text, max_sentences=3):
    prompt = (
        f"以下の英文を日本語に翻訳してください。"
        f"要旨の場合は、{max_sentences}文以内で簡潔にまとめてください。¥n¥n{text}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print("翻訳失敗:", e)
        return "(翻訳失敗)"

# === Slack通知関数 ===
def post_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print("Slack送信エラー:", response.text)

# === CrossRef検索＆処理 ===
def search_and_notify():
    for keyword in KEYWORDS:
        print(f"🔍 Searching keyword: {keyword}")
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
            title_en = item.get("title", [""])[0]
            abstract_en = item.get("abstract", None)
            doi = item.get("DOI", "")
            url = f"https://doi.org/{doi}"

            # タイトルにキーワードが含まれているか再チェック（大文字小文字区別なし）
            if not any(k.lower() in title_en.lower() for k in KEYWORDS):
                continue

            # 翻訳（タイトル・要旨）
            title_ja = translate_text_en_to_ja(title_en)
            if abstract_en:
                # CrossRefのabstractはHTMLタグやエンティティが入っていることが多いので簡単に除去
                import re
                abstract_plain = re.sub(r'<[^>]+>', '', abstract_en)
                abstract_plain = abstract_plain.replace('¥n', ' ').strip()
                abstract_ja = translate_text_en_to_ja(abstract_plain)
            else:
                abstract_ja = "（要旨なし）"

            # Slack投稿メッセージ作成
            message = (
                f"{title_en} / {title_ja}¥n"
                f"{url}¥n"
                f"{abstract_ja}"
            )
            print("Posting to Slack:¥n", message)
            post_to_slack(message)

            # API連続呼び出しを避けるため少し待機
            time.sleep(2)

if __name__ == "__main__":
    search_and_notify()
