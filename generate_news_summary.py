import nltk
from newspaper import Article
from transformers import pipeline, AutoTokenizer
import sys

# Download tokenizer
nltk.download('punkt', quiet=True)

# Constants
MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
MAX_INPUT_TOKENS = 1024
CHUNK_TOKEN_LIMIT = 950  # Slight buffer under max

# Load model and tokenizer once
summarizer = pipeline("summarization", model=MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def extract_article(url, lang='en'):
    article = Article(url, language=lang)
    article.download()
    article.parse()
    return article.title, article.text

def split_text_tokenwise(text):
    sentences = nltk.sent_tokenize(text)
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = len(tokenizer.encode(sentence, add_special_tokens=False))
        if current_tokens + sentence_tokens <= CHUNK_TOKEN_LIMIT:
            current_chunk += " " + sentence
            current_tokens += sentence_tokens
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_tokens = sentence_tokens

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def summarize_text(title, text):
    chunks = split_text_tokenwise(text)
    print(f"🔍 Total chunk(s): {len(chunks)}")

    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"🧠 Summarizing chunk {i+1}/{len(chunks)}")
        try:
            summary = summarizer(chunk, max_length=150, min_length=40, do_sample=False)[0]['summary_text']
            summaries.append(summary)
        except Exception as e:
            print(f"⚠️ Error summarizing chunk {i+1}: {e}")
            continue

    combined_summary = " ".join(summaries)
    return title.strip(), combined_summary.strip()

def main():
    lang = input("Language (en/bn): ").strip().lower()
    url = input("Paste the news article URL: ").strip()

    try:
        title, full_text = extract_article(url, lang)
        print(f"\n📰 Extracted Title:\n{title}")
        print(f"\n📝 Article Sample:\n{full_text[:300]}...\n")

        if lang == "bn":
            print("⚠️ Bangla summarization not supported. Translate first.")

        print("\nSummarizing article...")
        title, subtitle = summarize_text(title, full_text)

        print("\n=== Final Photocard Content ===")
        print(f"📌 Title (English): {title}")
        print(f"📝 Subtitle (English): {subtitle}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
