import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter.scrolledtext import ScrolledText
import threading
import os
import datetime
import webbrowser
from PIL import Image, ImageDraw, ImageFont, ImageTk
from newspaper import Article
from transformers import pipeline
import nltk

nltk.download('punkt', quiet=True)

# === Paths and constants ===
TEMPLATE_IMAGE = "tcb-template.png"
TCB_ICON = "tcb-icon.png"
FONT_PATH = "TiroBangla.ttf"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Pictures")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

# Initialize summarization pipeline
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# === Helper functions ===
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

def draw_multicolor_text(draw, position, text, font, colors, max_width, max_height):
    # text: string
    # colors: list of (start_idx, end_idx, (r,g,b,a))
    words = text.split()
    lines = []
    line = ''
    for w in words:
        test_line = (line + ' ' + w).strip()
        bbox = draw.textbbox((0,0), test_line, font=font)
        w_w = bbox[2] - bbox[0]
        if w_w <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)

    line_h = font.getbbox('A')[3] - font.getbbox('A')[1] + 4
    total_h = line_h * len(lines)
    x, y = position
    start_y = y + max(0, (max_height - total_h)//2)

    color_map = [(255,255,255,255)] * len(text)
    for start, end, col in colors:
        for i in range(start, end):
            if i < len(color_map):
                color_map[i] = col

    char_index = 0
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        line_w = bbox[2] - bbox[0]
        cur_x = x + (max_width - line_w)//2

        for ch in line:
            c = color_map[char_index] if char_index < len(color_map) else (255,255,255,255)
            draw.text((cur_x, start_y), ch, font=font, fill=c)
            char_w = draw.textbbox((0,0), ch, font=font)[2] - draw.textbbox((0,0), ch, font=font)[0]
            cur_x += char_w
            char_index += 1
        start_y += line_h

def generate_photocard(title, bg_path, template_path, font_path, output_path,
                       title_pos, title_font_size, title_box,
                       icon_pos, date_pos, colors):
    # Load background, resize to 1080 width maintaining aspect ratio
    bg = Image.open(bg_path).convert("RGBA")
    w_percent = 1080 / float(bg.size[0])
    h_size = int((float(bg.size[1]) * float(w_percent)))
    bg = bg.resize((1080, h_size), Image.LANCZOS)

    # Load template overlay
    overlay = Image.open(template_path).convert("RGBA")

    canvas_height = max(bg.size[1], overlay.size[1])
    canvas = Image.new("RGBA", (1080, canvas_height), (0,0,0,255))
    canvas.paste(bg, (0,0))
    canvas.alpha_composite(overlay, (0,0))

    draw = ImageDraw.Draw(canvas)

    # Draw TCB icon
    if os.path.exists(TCB_ICON):
        icon = Image.open(TCB_ICON).convert("RGBA")
        canvas.paste(icon, icon_pos, icon)

    # Draw date text
    date_font = ImageFont.truetype(font_path, 24)
    date_str = datetime.datetime.now().strftime("%d %B, %Y").upper()
    bbox = draw.textbbox((0,0), date_str, font=date_font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(date_pos, date_str, font=date_font, fill=(255,255,255,255))

    # Draw multi-colored title text in box area
    font_title = ImageFont.truetype(font_path, title_font_size)
    draw_multicolor_text(draw, title_pos, title, font_title, colors, title_box[0], title_box[1])

    # Crop to 1080x1280 final size
    final_img = canvas.crop((0, 0, 1080, 1280))
    final_img.save(output_path)
    return output_path, final_img

def merge_color_ranges(ranges):
    if not ranges:
        return []
    ranges.sort(key=lambda x: x[0])
    merged = [ranges[0]]
    for cur in ranges[1:]:
        last = merged[-1]
        if cur[0] <= last[1]:
            if cur[2] == last[2]:
                merged[-1] = (last[0], max(last[1], cur[1]), last[2])
            else:
                merged.append(cur)
        else:
            merged.append(cur)
    return merged

# === The Wizard GUI App ===
class TCBWizardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TCB News Photocard Generator")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # Data vars
        self.news_url = tk.StringVar()
        self.bg_image_path = None

        self.title_text = ""
        self.summary_text = ""
        self.full_text = ""

        self.title_x = tk.IntVar(value=150)
        self.title_y = tk.IntVar(value=880)
        self.title_font_size = tk.IntVar(value=36)
        self.title_max_w = tk.IntVar(value=700)
        self.title_max_h = tk.IntVar(value=200)

        self.icon_x = tk.IntVar(value=800)
        self.icon_y = tk.IntVar(value=20)

        self.date_x = tk.IntVar(value=800)
        self.date_y = tk.IntVar(value=1240)

        self.title_colors = [(0, 10000, (255,255,255,255))]  # default all white

        self.final_image_path = None

        # Frames
        self.frames = {}
        for FrameClass in (Step1Frame, Step2Frame, Step3Frame, Step4Frame):
            frame = FrameClass(self)
            self.frames[FrameClass] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame(Step1Frame)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()

    def choose_image(self):
        path = filedialog.askopenfilename(title="Select Background Image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.bg_image_path = path
            self.frames[Step1Frame].bg_label.config(text=os.path.basename(path))
            self.frames[Step1Frame].check_ready()

    def start_generation(self):
        if not self.news_url.get():
            messagebox.showerror("Input Error", "Please enter a news article URL.")
            return
        if not self.bg_image_path:
            messagebox.showerror("Input Error", "Please select a background image.")
            return

        self.show_frame(Step2Frame)
        self.frames[Step2Frame].start_process(self.news_url.get(), self.bg_image_path, self)

    def update_title_colors(self, new_colors):
        self.title_colors = new_colors
        self.frames[Step3Frame].update_preview()

# === Step 1 ===
class Step1Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        tk.Label(self, text="Enter News URL:", font=("Arial", 14)).pack(pady=10)
        self.url_entry = tk.Entry(self, textvariable=parent.news_url, font=("Arial", 12), width=70)
        self.url_entry.pack(pady=5)

        self.bg_btn = tk.Button(self, text="Choose Photo Related to News", command=parent.choose_image)
        self.bg_btn.pack(pady=5)

        self.bg_label = tk.Label(self, text="No image selected")
        self.bg_label.pack(pady=5)

        self.gen_btn = tk.Button(self, text="Generate Photocard", state="disabled", command=parent.start_generation)
        self.gen_btn.pack(pady=15)

        def check_ready(*args):
            self.gen_btn.config(state="normal" if (parent.news_url.get() and parent.bg_image_path) else "disabled")

        parent.news_url.trace_add('write', check_ready)
        self.check_ready = check_ready

# === Step 2 ===
class Step2Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        tk.Label(self, text="Processing...", font=("Arial", 16)).pack(pady=10)
        self.log_box = ScrolledText(self, height=20, width=100, state="disabled", font=("Courier", 10))
        self.log_box.pack(padx=10, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=600)
        self.progress_bar.pack(pady=5)

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def start_process(self, url, bg_image_path, app):
        def task():
            try:
                self.log("Extracting article from URL...")
                title, full_text = extract_article(url)
                self.progress_var.set(20)
                self.log(f"Title extracted: {title}")

                self.log("Summarizing article...")
                summary = summarize_article(full_text)
                self.progress_var.set(60)
                self.log("Summary generated.")

                app.title_text = title
                app.summary_text = summary
                app.full_text = full_text

                self.progress_var.set(80)
                self.log("Preparing photocard preview...")
                self.progress_var.set(100)
                self.log("Done!")

                app.show_frame(Step3Frame)
                app.frames[Step3Frame].load_preview()
            except Exception as e:
                self.log(f"Error: {e}")
                messagebox.showerror("Error", f"Processing failed: {e}")
                app.show_frame(Step1Frame)

        threading.Thread(target=task, daemon=True).start()

# === Step 3 ===
class Step3Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Left preview canvas
        self.canvas = tk.Canvas(self, width=540, height=640, bg="black")
        self.canvas.pack(side="left", padx=10, pady=10)

        # Right controls
        control_frame = tk.Frame(self)
        control_frame.pack(side="right", fill="y", padx=10, pady=10)

        # Title sliders
        tk.Label(control_frame, text="Title X:").pack()
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.title_x, command=lambda e:self.update_preview()).pack(fill="x")
        tk.Label(control_frame, text="Title Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.title_y, command=lambda e:self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Font Size:").pack()
        tk.Scale(control_frame, from_=10, to=80, orient="horizontal", variable=parent.title_font_size, command=lambda e:self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Max Width:").pack()
        tk.Scale(control_frame, from_=200, to=900, orient="horizontal", variable=parent.title_max_w, command=lambda e:self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Max Height:").pack()
        tk.Scale(control_frame, from_=50, to=600, orient="horizontal", variable=parent.title_max_h, command=lambda e:self.update_preview()).pack(fill="x")

        # Icon sliders
        tk.Label(control_frame, text="TCB Icon X:").pack(pady=(20,0))
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.icon_x, command=lambda e:self.update_preview()).pack(fill="x")
        tk.Label(control_frame, text="TCB Icon Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.icon_y, command=lambda e:self.update_preview()).pack(fill="x")

        # Date sliders
        tk.Label(control_frame, text="Date X:").pack(pady=(20,0))
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.date_x, command=lambda e:self.update_preview()).pack(fill="x")
        tk.Label(control_frame, text="Date Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.date_y, command=lambda e:self.update_preview()).pack(fill="x")

        # Title Text widget for partial color editing
        tk.Label(control_frame, text="Edit Title Text (select portion and pick color):").pack(pady=(10,0))
        self.title_text_widget = tk.Text(control_frame, height=6, width=40, wrap="word", font=("TiroBangla", 16))
        self.title_text_widget.pack()

        color_btn = tk.Button(control_frame, text="Pick Color for Selection", command=self.pick_color_for_selection)
        color_btn.pack(pady=5)

        self.finalize_btn = tk.Button(self, text="Finalize & Prepare Articles", font=("Arial", 14), command=self.finalize)
        self.finalize_btn.pack(pady=5)

        self.title_text_widget.bind("<<Modified>>", self.on_text_change)

        self.preview_img = None
        self.tk_preview_img = None

    def on_text_change(self, event=None):
        self.title_text_widget.edit_modified(False)
        self.parent.title_text = self.title_text_widget.get("1.0", "end-1c")
        self.parent.update_title_colors(self.parent.title_colors)  # refresh

    def load_preview(self):
        self.title_text_widget.delete("1.0", tk.END)
        self.title_text_widget.insert(tk.END, self.parent.title_text)
        self.clear_tags()
        self.apply_colors_to_text_widget()
        self.update_preview()

    def clear_tags(self):
        for tag in self.title_text_widget.tag_names():
            self.title_text_widget.tag_delete(tag)

    def apply_colors_to_text_widget(self):
        self.clear_tags()
        for i, (start, end, color) in enumerate(self.parent.title_colors):
            tag_name = f"color{i}"
            r,g,b,a = color
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            start_idx = f"1.{start}"
            end_idx = f"1.{end}"
            self.title_text_widget.tag_add(tag_name, start_idx, end_idx)
            self.title_text_widget.tag_config(tag_name, foreground=hex_color)

    def pick_color_for_selection(self):
        try:
            start = self.title_text_widget.index("sel.first")
            end = self.title_text_widget.index("sel.last")
        except tk.TclError:
            messagebox.showinfo("No Selection", "Please select a portion of the title text to color.")
            return

        color_code = colorchooser.askcolor(title="Choose color for selected text")
        if not color_code or not color_code[0]:
            return
        rgb = tuple(int(x) for x in color_code[0]) + (255,)

        start_idx = int(start.split('.')[1])
        end_idx = int(end.split('.')[1])

        new_colors = []
        for s,e,c in self.parent.title_colors:
            if e <= start_idx or s >= end_idx:
                new_colors.append((s,e,c))
            else:
                if s < start_idx:
                    new_colors.append((s, start_idx, c))
                if e > end_idx:
                    new_colors.append((end_idx, e, c))
        new_colors.append((start_idx, end_idx, rgb))
        new_colors = merge_color_ranges(new_colors)

        self.parent.update_title_colors(new_colors)
        self.apply_colors_to_text_widget()
        self.update_preview()

    def update_preview(self):
        try:
            path, img = generate_photocard(
                self.parent.title_text,
                self.parent.bg_image_path,
                TEMPLATE_IMAGE,
                FONT_PATH,
                output_path=os.path.join(OUTPUT_DIR, "preview.png"),
                title_pos=(self.parent.title_x.get(), self.parent.title_y.get()),
                title_font_size=self.parent.title_font_size.get(),
                title_box=(self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                icon_pos=(self.parent.icon_x.get(), self.parent.icon_y.get()),
                date_pos=(self.parent.date_x.get(), self.parent.date_y.get()),
                colors=self.parent.title_colors,
            )
            self.preview_img = img.resize((540, 640), Image.LANCZOS)
            self.tk_preview_img = ImageTk.PhotoImage(self.preview_img)
            self.canvas.delete("all")
            self.canvas.create_image(0,0,anchor="nw", image=self.tk_preview_img)
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(270, 320, text=f"Preview Error:\n{e}", fill="red", font=("Arial", 14), justify="center")

    def finalize(self):
        # Save final image and move to step 4
        try:
            filename = self.parent.title_text[:50].replace(" ", "_").replace("/", "-") + ".png"
            out_path = os.path.join(OUTPUT_DIR, filename)
            generate_photocard(
                self.parent.title_text,
                self.parent.bg_image_path,
                TEMPLATE_IMAGE,
                FONT_PATH,
                output_path=out_path,
                title_pos=(self.parent.title_x.get(), self.parent.title_y.get()),
                title_font_size=self.parent.title_font_size.get(),
                title_box=(self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                icon_pos=(self.parent.icon_x.get(), self.parent.icon_y.get()),
                date_pos=(self.parent.date_x.get(), self.parent.date_y.get()),
                colors=self.parent.title_colors,
            )
            self.parent.final_image_path = out_path
            self.parent.show_frame(Step4Frame)
            self.parent.frames[Step4Frame].load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save final photocard: {e}")

# === Step 4 ===
class Step4Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        tk.Label(self, text="Photocard Created!", font=("Arial", 18)).pack(pady=10)

        self.path_label = tk.Label(self, text="", fg="blue", cursor="hand2")
        self.path_label.pack()
        self.path_label.bind("<Button-1>", self.open_folder)

        tk.Label(self, text="📝 Summary").pack(pady=(15,0))
        self.summary_box = ScrolledText(self, height=6, width=90)
        self.summary_box.pack(padx=10)

        self.copy_summary_btn = tk.Button(self, text="Copy Summary", command=self.copy_summary)
        self.copy_summary_btn.pack(pady=5)

        tk.Label(self, text="📄 Full Article + Source").pack(pady=(10,0))
        self.full_box = ScrolledText(self, height=10, width=90)
        self.full_box.pack(padx=10)

        self.copy_full_btn = tk.Button(self, text="Copy Full Article", command=self.copy_full)
        self.copy_full_btn.pack(pady=5)

        self.another_btn = tk.Button(self, text="Make Another Photocard ", command=self.make_another)
        self.another_btn.pack(pady=20)

    def load_data(self):
        self.path_label.config(text=f"Saved to: {self.parent.final_image_path}")

        self.summary_box.delete("1.0", tk.END)
        self.summary_box.insert(tk.END, self.parent.summary_text)

        self.full_box.delete("1.0", tk.END)
        self.full_box.insert(tk.END, self.parent.full_text + f"\n\nSource: {self.parent.news_url.get()}")

    def open_folder(self, event=None):
        folder = os.path.dirname(self.parent.final_image_path)
        webbrowser.open(folder)

    def copy_summary(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.summary_box.get("1.0", tk.END))

    def copy_full(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.full_box.get("1.0", tk.END))

    def make_another(self):
        # Reset all data and go back to step 1
        self.parent.news_url.set("")
        self.parent.bg_image_path = None
        self.parent.title_text = ""
        self.parent.summary_text = ""
        self.parent.full_text = ""

        self.parent.title_x.set(150)
        self.parent.title_y.set(880)
        self.parent.title_font_size.set(36)
        self.parent.title_max_w.set(700)
        self.parent.title_max_h.set(200)

        self.parent.icon_x.set(800)
        self.parent.icon_y.set(20)
        self.parent.date_x.set(800)
        self.parent.date_y.set(1240)

        self.parent.title_colors = [(0, 10000, (255,255,255,255))]

        self.parent.show_frame(Step1Frame)
        self.parent.frames[Step1Frame].bg_label.config(text="No image selected")
        self.parent.frames[Step1Frame].gen_btn.config(state="disabled")

if __name__ == "__main__":
    app = TCBWizardApp()
    app.mainloop()
