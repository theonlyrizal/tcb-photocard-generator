import requests
from newspaper import Article
import nltk
from transformers import pipeline
import sys
import time
import re

# Download punkt tokenizer (for English)
nltk.download('punkt', quiet=True)

def extract_article(url, lang='en'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
                      '(KHTML, like Gecko) Chrome/115.0 Safari/537.36'
    }
    article = Article(url, language=lang, request_headers=headers)
    article.download()
    article.parse()
    return article.title.strip(), article.text.strip()

def naive_bangla_sentence_split(text):
    # Split by Bengali full stop (।), exclamation, question mark
    return re.split(r'(?<=[।!?])\s+', text.strip())

def translate_text(text, source="bn", target="en"):
    url = "https://libretranslate.de/translate"
    max_chunk = 1000

    if source == "bn":
        sentences = naive_bangla_sentence_split(text)
    else:
        sentences = nltk.sent_tokenize(text)

    chunks = []
    chunk = ""
    for s in sentences:
        if len(chunk) + len(s) + 1 > max_chunk:
            chunks.append(chunk.strip())
            chunk = s
        else:
            chunk += " " + s
    if chunk:
        chunks.append(chunk.strip())

    translated_chunks = []
    for i, chunk in enumerate(chunks):
        data = {
            "q": chunk,
            "source": source,
            "target": target,
            "format": "text"
        }
        try:
            response = requests.post(url, data=data, timeout=15)
            if response.status_code == 200:
                translated_chunks.append(response.json()["translatedText"])
            else:
                print(f"⚠️ Translation chunk {i+1} failed with status {response.status_code}")
                return None
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Translation chunk {i+1} failed: {e}")
            return None
    return " ".join(translated_chunks)

def summarize_text(text):
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    summary = summarizer(text, max_length=50, min_length=20, do_sample=False)[0]['summary_text']
    return summary.strip()

def main():
    lang = input("Language (en/bn): ").strip().lower()
    url = input("Paste the news article URL: ").strip()

    try:
        title, full_text = extract_article(url, lang)
        print(f"\n📰 Extracted Title:\n{title}")
        print(f"\n📝 Article Sample:\n{full_text[:300]}...\n")

        if lang == "bn":
            print("Translating Bangla article to English...")
            translated = translate_text(full_text, source="bn", target="en")
            if not translated:
                print("❌ Error: Translation failed.")
                return
            text_to_summarize = translated
        else:
            text_to_summarize = full_text

        print("Summarizing the subtitle text...")
        summary = summarize_text(text_to_summarize)

        print("\n=== Final Photocard Content ===")
        print(f"📌 Title (English): {title if lang == 'en' else '[Translate manually]'}")
        print(f"📝 Subtitle (English): {summary}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
