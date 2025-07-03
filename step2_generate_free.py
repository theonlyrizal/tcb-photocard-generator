from transformers import pipeline

def generate_title_subtitle(article_title, article_text):
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

    # Summarize article text for subtitle
    summary_result = summarizer(article_text, max_length=50, min_length=20, do_sample=False)
    subtitle = summary_result[0]['summary_text']

    # Trim or reuse input title
    title = article_title.strip()
    if len(title) > 60:
        title = title[:57] + "..."

    return title, subtitle

def main():
    print("Paste the article title:")
    title = input()

    print("Paste the article text (end with an empty line):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    text = "\n".join(lines)

    gen_title, gen_subtitle = generate_title_subtitle(title, text)

    print("\n=== Generated Photocard Content ===")
    print(f"📌 Title (English): {gen_title}")
    print(f"📝 Subtitle (English): {gen_subtitle}")

if __name__ == "__main__":
    main()
