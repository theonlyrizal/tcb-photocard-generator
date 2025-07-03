from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

def generate_photocard(title, subtitle, background_image_path, output_path, font_path):
    # Open the photocard template image
    image = Image.open(background_image_path).convert("RGBA")

    draw = ImageDraw.Draw(image)

    # Load font (adjust size as needed)
    font_size = 48
    font = ImageFont.truetype(font_path, font_size)

    # Define text box area (x, y, width, height) where title will appear on the photocard
    # Adjust these values to fit your template design
    x, y = 100, 100
    max_width = image.width - 2 * x
    max_height = image.height - 200

    # Wrap title text to fit max_width
    lines = []
    for line in title.split('\n'):
        wrapped = textwrap.wrap(line, width=30)  # tweak width for your font & size
        lines.extend(wrapped if wrapped else [''])

    # Calculate total height of text block
    line_height = font.getsize('A')[1] + 10  # line height + spacing
    total_text_height = line_height * len(lines)

    # Start drawing text vertically centered in the box area
    current_y = y + (max_height - total_text_height) // 2

    # Draw each line of the title centered horizontally
    for line in lines:
        w, h = draw.textsize(line, font=font)
        draw.text(((image.width - w) / 2, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += line_height

    # Save the final photocard image
    image.save(output_path)
    print(f"Photocard saved to {output_path}")

    # Return the subtitle separately for caption or comments
    return subtitle

if __name__ == "__main__":
    # Example usage
    title = "Bangladesh to build 100 cold storages for agricultural goods, Advisor Jahangir says"
    subtitle = (
        "Home Advisor Jahangir Alam Chowdhury said at least 100 cold storage facilities "
        "are being constructed by both small and large companies across Bangladesh "
        "to preserve raw materials, including vegetables. He made the remarks following "
        "a meeting to review the overall progress of projects under the Ministry of Agriculture. "
        "Those involved in recent incidents of torture and rape in Muradnagar and Bhola in Cumilla "
        "have been and are being brought to justice quickly. Read full details in comments below."
    )

    background_image = "template.png"  # Your photocard template file
    output_file = "photocard_output.png"
    font_file = "Roboto-Regular.ttf"  # Path to your .ttf font file

    caption_text = generate_photocard(title, subtitle, background_image, output_file, font_file)

    print("\n--- Facebook Post Caption ---")
    print(caption_text)
