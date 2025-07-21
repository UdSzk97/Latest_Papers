import requests
import datetime
import os
import openai
import time
import re

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

# === タイトル翻訳関数 ===
def translate_title_en_to_ja(text):
    prompt = (
        f"以下の英文タイトルを自然でわかりやすい日本語に翻訳してください。\n\n{text}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        translated = response.choices[0].message['content'].strip()
        translated = translated.replace('¥n', '\n').replace('\\n', '\n')
        return translated
    except Exception as e:
        print("タイトル翻訳失敗:", e)
        return "(翻訳失敗)"

# === キーワード抽出関数（英語） ===
def extract_keywords_en(title, abstract):
    text_for_prompt = f"Title: {title}\nAbstract: {abstract if abstract else 'No abstract provided.'}\n\n" \
                      "Please extract up to 5 important keywords or phrases in English that represent the main topics of this paper, in bullet points."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert scientific assistant."},
                {"role": "user", "content": text_for_prompt},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        keywords_text = response.choices[0].message['content'].strip()
        keywords_text = keywords_text.replace('¥n', '\n').replace('\\n', '\n')
        return keywords_text
    except Exception as e:
        print("OpenAI keyword extraction error:", e)
        return "(Keyword extraction failed)"

# === Slack通知関数 ===
def post_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print("Slack sending error:", response.text)

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

            # 要旨のHTMLタグ除去・改行除去
            if abstract_en:
                abstract_plain = re.sub(r'<[^>]+>', '', abstract_en)
                abstract_plain = abstract_plain.replace('¥n', ' ').replace('\\n', ' ').strip()
            else:
                abstract_plain = ""

            # タイトル日本語訳
            title_ja = translate_title_en_to_ja(title_en)

            # OpenAIで英語キーワード抽出
            keywords_en = extract_keywords_en(title_en, abstract_plain)

            # Slack投稿メッセージ作成
            message = (
                f"{title_en} / {title_ja}\n"
                f"{url}\n"
                f"Keywords:\n{keywords_en}"
            )
            print("Posting to Slack:\n", message)
            post_to_slack(message)

            # API連続呼び出しを避けるため少し待機
            time.sleep(2)

if __name__ == "__main__":
    search_and_notify()
