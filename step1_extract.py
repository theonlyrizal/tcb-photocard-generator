from newspaper import Article
from langdetect import detect, LangDetectException

user_lang = input("Language (en/bn): ").strip().lower()
if user_lang not in ['en', 'bn']:
    user_lang = 'en'

news_url = input("Paste the news URL: ")

use_lang = user_lang
article = Article(news_url, language=use_lang)
article.download()
article.parse()

text = article.text

if not text.strip():
    print("\n⚠️ Warning: No article text extracted. Language detection skipped.")
    detected_lang = 'unknown'
else:
    try:
        detected_lang = detect(text)
    except LangDetectException:
        detected_lang = 'unknown'

print(f"\nDetected language: {detected_lang}")
print(f"User selected language: {user_lang}")

if detected_lang != 'unknown':
    if (user_lang == 'bn' and detected_lang != 'bn') or (user_lang == 'en' and detected_lang != 'en'):
        print("\n⚠️ Warning: The detected language of the article does NOT match your selection.")
        print("Please double-check the URL or language choice.\n")

print("\n📰 Title:")
print(article.title)

print("\n📝 Full article text:")
print(text)
