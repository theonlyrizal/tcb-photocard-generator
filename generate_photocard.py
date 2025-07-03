from PIL import Image, ImageDraw, ImageFont
import textwrap
from datetime import datetime

def generate_photocard(title, subtitle, background_image_path, output_path, font_path):
    # Open template
    image = Image.open(background_image_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Font settings
    font_size = 36
    font = ImageFont.truetype(font_path, font_size)

    # Title box
    x, y = 100, 950
    max_width = 880
    max_height = 280

    # Wrap title
    lines = []
    for line in title.split('\n'):
        wrapped = textwrap.wrap(line, width=30)
        lines.extend(wrapped if wrapped else [''])

    # Title positioning
    line_height = font.getbbox('A')[3] - font.getbbox('A')[1] + 10
    total_text_height = line_height * len(lines)
    current_y = y + (max_height - total_text_height) // 2

    for line in lines:
        w = font.getbbox(line)[2]
        draw.text(((image.width - w) / 2, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += line_height

    # 📆 Add current date at bottom right
    now = datetime.now()
    date_str = now.strftime("%d %B, %Y").upper()  # e.g., "11 JULY, 2025"

    # Load smaller font for date
    date_font = ImageFont.truetype(font_path, 28)
    date_width, date_height = date_font.getbbox(date_str)[2:]

    margin = 40
    date_x = image.width - date_width - margin
    date_y = image.height - date_height - margin
    draw.text((date_x, date_y), date_str, font=date_font, fill=(255, 255, 255, 255))

    # Save image
    image.save(output_path)
    print(f"✅ Photocard saved to: {output_path}")

    return subtitle

if __name__ == "__main__":
    title = "Bangladesh to build 100 cold storages for agricultural goods, Advisor Jahangir says"
    subtitle = (
        "Home Advisor Jahangir Alam Chowdhury said at least 100 cold storage facilities are being constructed "
        "by both small and large companies across Bangladesh to preserve raw materials, including vegetables. "
        "He made the remarks following a meeting to review the overall progress of projects under the Ministry of Agriculture. "
        "Those involved in recent incidents of torture and rape in Muradnagar and Bhola in Cumilla have been and are being brought to justice quickly. "
        "Read full details in comments below."
    )

    background_image = "tcb-template.png"
    output_file = "C:/Users/Rizal/Pictures/photocard_output.png"
    font_file = "TiroBangla.ttf"

    caption_text = generate_photocard(title, subtitle, background_image, output_file, font_file)

    print("\n--- Facebook Caption ---")
    print(caption_text)
