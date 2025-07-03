from newspaper import Article
from transformers import pipeline
from PIL import Image, ImageDraw, ImageFont
import textwrap
import nltk
import datetime
import os
import sys

nltk.download('punkt', quiet=True)

# Paths
BACKGROUND_IMAGE = "tcb-template.png"
OUTPUT_IMAGE_PATH = os.path.expanduser("~/Pictures/tcb_photocard_output.png")
FONT_PATH = "TiroBangla.ttf"  # Make sure this font file exists in your dir or give full path

# === STEP 1 & 2: Article Extraction and Summarization ===
def extract_article(url, lang='en'):
    article = Article(url, language=lang)
    article.download()
    article.parse()
    return article.title.strip(), article.text.strip()

def summarize_text(text):
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    max_chunk_tokens = 1000
    chunks = []
    words = text.split()
    chunk = []
    length = 0
    for word in words:
        length += len(word) + 1
        chunk.append(word)
        if length > max_chunk_tokens:
            chunks.append(" ".join(chunk))
            chunk = []
            length = 0
    if chunk:
        chunks.append(" ".join(chunk))

    final_summary = []
    print(f"\n🔍 Total chunks: {len(chunks)}")
    for i, chunk_text in enumerate(chunks):
        print(f"🧠 Summarizing chunk {i+1}/{len(chunks)}...")
        try:
            out = summarizer(chunk_text, max_length=150, min_length=40, do_sample=False)
            final_summary.append(out[0]['summary_text'])
        except Exception as e:
            print(f"⚠️ Error summarizing chunk {i+1}: {e}")
    return " ".join(final_summary)

# === STEP 3: Photocard Generation ===
def generate_photocard(title, subtitle, background_image_path, output_path, font_path):
    image = Image.open(background_image_path).convert("RGBA")
    draw = ImageDraw.Draw(image)
    font_size = 32
    font = ImageFont.truetype(font_path, font_size)

    x, y = 150, 880
    max_width = 880
    max_height = 300

    lines = []
    for line in title.split('\n'):
        wrapped = textwrap.wrap(line, width=30)
        lines.extend(wrapped if wrapped else [''])

    line_height = font.getbbox('A')[3] - font.getbbox('A')[1] + 10
    total_text_height = line_height * len(lines)
    current_y = y + (max_height - total_text_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((image.width - w) / 2, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += line_height

    # Add date at bottom right
    date_font = ImageFont.truetype(font_path, 24)
    date_str = datetime.datetime.now().strftime("%d %B, %Y").upper()
    date_bbox = draw.textbbox((0, 0), date_str, font=date_font)
    date_w = date_bbox[2] - date_bbox[0]
    date_h = date_bbox[3] - date_bbox[1]
    draw.text((image.width - date_w - 30, image.height - date_h - 30), date_str, font=date_font, fill=(255, 255, 255, 255))

    image.save(output_path)
    print(f"\n📸 Photocard saved to: {output_path}")
    return subtitle

# === MAIN ===
def main():
    lang = input("Language (en/bn): ").strip().lower()
    url = input("Paste the news article URL: ").strip()

    try:
        print("\nExtracting article...")
        title, full_text = extract_article(url, lang)
        print(f"\n📰 Extracted Title:\n{title}")
        print(f"\n📝 Article Sample:\n{full_text[:500]}...\n")

        if lang == "bn":
            print("⚠️ Bangla summarization not supported. Translate first.")

        print("Summarizing article...")
        subtitle = summarize_text(full_text)

        print("\n=== Final Photocard Content ===")
        print(f"📌 Title (English): {title}")
        print(f"📝 Subtitle (English): {subtitle[:300]}...")

        generate_photocard(title, subtitle, BACKGROUND_IMAGE, OUTPUT_IMAGE_PATH, FONT_PATH)

        print("\n✅ All done. Copy the subtitle as Facebook caption. Paste full article in comment with source.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
