import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import webbrowser
import threading
import os
import datetime
from PIL import Image, ImageDraw, ImageFont
from newspaper import Article
from transformers import pipeline
import nltk

nltk.download('punkt', quiet=True)

# Paths
TEMPLATE_IMAGE = "tcb-template.png"
FONT_PATH = "TiroBangla.ttf"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Pictures")

# Summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Utility functions
def extract_article(url):
    article = Article(url, language='en')
    article.download()
    article.parse()
    return article.title.strip(), article.text.strip()

def summarize_article(text):
    max_chunk = 800
    paragraphs = text.split("\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_chunk:
            current += " " + para
        else:
            chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())

    summary = " ".join([summarizer(chunk, max_length=80, min_length=20, do_sample=False)[0]['summary_text'] for chunk in chunks])
    return summary.strip()

def generate_photocard(title, bg_path, template_path, font_path, output_path):
    # Load background and resize to width=1080 while maintaining aspect ratio
    bg = Image.open(bg_path).convert("RGBA")
    w_percent = 1080 / float(bg.size[0])
    h_size = int((float(bg.size[1]) * float(w_percent)))
    bg = bg.resize((1080, h_size), Image.LANCZOS)

    # Load transparent overlay template
    overlay = Image.open(template_path).convert("RGBA")

    # Create canvas with height = max(bg, template)
    canvas_height = max(bg.size[1], overlay.size[1])
    canvas = Image.new("RGBA", (1080, canvas_height), (0, 0, 0, 255))
    canvas.paste(bg, (0, 0))
    canvas.alpha_composite(overlay, (0, 0))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(font_path, 36)

    # Wrap and draw title
    wrapped = []
    for line in title.split('\n'):
        wrapped.extend(line.strip() for line in line.split('. '))
    y = 880
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((1080 - w) // 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += h + 10

    # Draw date
    date_font = ImageFont.truetype(font_path, 24)
    date_str = datetime.datetime.now().strftime("%d %B, %Y").upper()
    w, h = draw.textbbox((0, 0), date_str, font=date_font)[2:]
    draw.text((1080 - w - 30, 1280 - h - 20), date_str, font=date_font, fill=(255, 255, 255, 255))

    canvas = canvas.crop((0, 0, 1080, 1280))  # Ensure final image is 1080x1280
    canvas.save(output_path)
    return output_path

# GUI Logic
selected_bg_path = None

def choose_background():
    global selected_bg_path
    path = filedialog.askopenfilename(title="Select Background Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if path:
        selected_bg_path = path
        bg_label.config(text=os.path.basename(path))

def run_process():
    url = url_entry.get()
    lang = lang_var.get()

    if not url:
        messagebox.showerror("Input Error", "Please enter a news article URL.")
        return

    if not selected_bg_path:
        messagebox.showerror("Input Error", "Please select a background image.")
        return

    def process():
        try:
            status.set("Extracting article...")
            title, full_text = extract_article(url)
            status.set("Summarizing article...")
            summary = summarize_article(full_text)

            filename = title[:50].replace(" ", "_").replace("/", "-") + ".png"
            output_path = os.path.join(OUTPUT_DIR, filename)

            status.set("Generating photocard...")
            generate_photocard(title, selected_bg_path, TEMPLATE_IMAGE, FONT_PATH, output_path)

            status.set(f"✅ Saved to: {output_path}")
            open_button.config(command=lambda: webbrowser.open(os.path.dirname(output_path)))

            summary_box.delete('1.0', tk.END)
            summary_box.insert(tk.END, summary)

            full_box.delete('1.0', tk.END)
            full_box.insert(tk.END, full_text + f"\n\nSource: {url}")

        except Exception as e:
            status.set(f"❌ Error: {e}")

    threading.Thread(target=process).start()

# GUI Setup
root = tk.Tk()
root.title("TCB News Photocard Generator")
root.geometry("800x750")

url_entry = tk.Entry(root, font=("Arial", 12), width=70)
url_entry.pack(pady=10)

lang_var = tk.StringVar(value="en")
tk.Radiobutton(root, text="English", variable=lang_var, value="en").pack(side="left", padx=10)
tk.Radiobutton(root, text="Bangla (not supported)", variable=lang_var, value="bn").pack(side="left")

go_button = tk.Button(root, text="GO!", font=("Arial", 14), command=run_process)
go_button.pack(pady=10)

bg_select = tk.Button(root, text="Choose Background Image", command=choose_background)
bg_select.pack()
bg_label = tk.Label(root, text="No background selected")
bg_label.pack()

status = tk.StringVar()
status.set("Ready.")
status_label = tk.Label(root, textvariable=status, fg="green")
status_label.pack()

open_button = tk.Button(root, text="Open Folder", state="normal")
open_button.pack(pady=5)

tk.Label(root, text="📝 Subtitle").pack()
summary_box = scrolledtext.ScrolledText(root, height=4)
summary_box.pack(fill="x", padx=10)

copy1 = tk.Button(root, text="Copy Subtitle", command=lambda: root.clipboard_append(summary_box.get("1.0", tk.END)))
copy1.pack()

tk.Label(root, text="📄 Full Article + Source").pack()
full_box = scrolledtext.ScrolledText(root, height=8)
full_box.pack(fill="x", padx=10)

copy2 = tk.Button(root, text="Copy Full Text", command=lambda: root.clipboard_append(full_box.get("1.0", tk.END)))
copy2.pack()

root.mainloop()
