import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import os
import datetime
import webbrowser

# === Config ===
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Pictures")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TEMPLATE_IMAGE = "tcb-template.png"
TCB_ICON = "tcb-icon.png"
FONT_PATH = "TiroBangla.ttf"

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

# Dummy functions for article extraction & summarization — replace these!
def extract_article(url):
    # Simulate extracting title and full article text
    title = "Example News Title Extracted From URL"
    full_text = ("This is the full article text fetched from the URL you entered. "
                 "It contains all details and paragraphs. " * 5).strip()
    return title, full_text

def summarize_article(text):
    # Simulate summarizing
    return "This is a short summary of the article. It highlights the main points."

# Helper: save the photocard image with current settings
def save_photocard(title, bg_path, icon_path, font_path, 
                   title_pos, title_font_size, title_box,
                   icon_pos, date_pos, title_color):
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Draw TCB icon
    icon = Image.open(icon_path).convert("RGBA")
    icon_w, icon_h = icon.size
    img.paste(icon, icon_pos, icon)

    # Draw date in bottom right corner
    date_str = datetime.datetime.now().strftime("%d %B, %Y").upper()
    font_date = ImageFont.truetype(font_path, 20)
    dw, dh = draw.textsize(date_str, font=font_date)
    draw.text(date_pos, date_str, font=font_date, fill=(255,255,255,255))

    # Draw wrapped title text inside box with font size and color
    font_title = ImageFont.truetype(font_path, title_font_size)
    x, y = title_pos
    max_w, max_h = title_box

    # Simple wrap based on chars (could improve)
    lines = []
    words = title.split()
    line = ""
    for w in words:
        test_line = line + (" " if line else "") + w
        w_w, w_h = draw.textsize(test_line, font=font_title)
        if w_w <= max_w:
            line = test_line
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)

    # Draw lines vertically within max_h, center horizontally
    line_h = font_title.getsize("A")[1] + 4
    total_h = line_h * len(lines)
    start_y = y + max(0, (max_h - total_h)//2)
    for line in lines:
        w_line, _ = draw.textsize(line, font=font_title)
        draw.text((x + (max_w - w_line)//2, start_y), line, font=font_title, fill=title_color)
        start_y += line_h

    # Save output file
    filename = title[:50].replace(" ", "_").replace("/", "-") + ".png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path)
    return output_path, img

# === GUI App ===
class TCBWizardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TCB News Photocard Generator")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # Data storage
        self.news_url = tk.StringVar()
        self.bg_image_path = None
        self.title_text = ""
        self.summary_text = ""
        self.full_text = ""

        # Title customization vars
        self.title_x = tk.IntVar(value=150)
        self.title_y = tk.IntVar(value=880)
        self.title_font_size = tk.IntVar(value=36)
        self.title_max_w = tk.IntVar(value=700)
        self.title_max_h = tk.IntVar(value=200)

        self.icon_x = tk.IntVar(value=800)
        self.icon_y = tk.IntVar(value=20)

        self.date_x = tk.IntVar(value=800)
        self.date_y = tk.IntVar(value=1240)

        self.title_color = (255,255,255,255)  # white RGBA

        # Frames
        self.frames = {}
        for F in (Step1Frame, Step2Frame, Step3Frame, Step4Frame):
            frame = F(self)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame(Step1Frame)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.bg_image_path = path
            self.frames[Step1Frame].bg_label.config(text=os.path.basename(path))
            self.frames[Step1Frame].check_ready()

    def start_generation(self):
        if not self.news_url.get() or not self.bg_image_path:
            messagebox.showerror("Input error", "Please enter a URL and select a background image.")
            return

        self.show_frame(Step2Frame)
        self.frames[Step2Frame].start_process(
            self.news_url.get(),
            self.bg_image_path,
            self
        )

    def update_title_color(self, new_color):
        self.title_color = new_color
        self.frames[Step3Frame].update_preview()

# === Step 1 Frame: Input ===
class Step1Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        tk.Label(self, text="Enter News URL:", font=("Arial", 14)).pack(pady=10)
        self.url_entry = tk.Entry(self, textvariable=parent.news_url, font=("Arial", 12), width=70)
        self.url_entry.pack(pady=5)

        self.bg_button = tk.Button(self, text="Choose Photo Related to News", command=parent.choose_image)
        self.bg_button.pack(pady=5)

        self.bg_label = tk.Label(self, text="No image selected")
        self.bg_label.pack(pady=5)

        self.gen_button = tk.Button(self, text="Generate Photocard", state="disabled", command=parent.start_generation)
        self.gen_button.pack(pady=15)

        # check if inputs ready to enable generate button
        def check_ready(*args):
            self.gen_button.config(state="normal" if (parent.news_url.get() and parent.bg_image_path) else "disabled")

        parent.news_url.trace_add('write', check_ready)
        self.check_ready = check_ready

# === Step 2 Frame: Progress ===
class Step2Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        tk.Label(self, text="Processing...", font=("Arial", 16)).pack(pady=10)

        self.log_box = ScrolledText(self, height=20, width=100, state="disabled", font=("Courier", 10))
        self.log_box.pack(padx=10, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=600)
        self.progress_bar.pack(pady=5)

        self.parent = parent

    def log(self, message):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def start_process(self, url, bg_image_path, app):
        # Run extraction, summarization in a thread and update progress
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

                # Save data to app
                app.title_text = title
                app.summary_text = summary
                app.full_text = full_text

                self.progress_var.set(80)
                self.log("Preparing photocard preview...")

                # Once done, show step 3 frame on main thread
                self.progress_var.set(100)
                self.log("Done!")

                app.show_frame(Step3Frame)
                app.frames[Step3Frame].load_preview()

            except Exception as e:
                self.log(f"Error: {e}")
                messagebox.showerror("Error", f"Processing failed: {e}")
                app.show_frame(Step1Frame)

        threading.Thread(target=task, daemon=True).start()

# === Step 3 Frame: Interactive Preview & Placement ===
class Step3Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Title positioning sliders
        control_frame = tk.Frame(self)
        control_frame.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(control_frame, text="Title X:").pack()
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.title_x,
                 command=lambda e: self.update_preview()).pack(fill="x")
        tk.Label(control_frame, text="Title Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.title_y,
                 command=lambda e: self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Font Size:").pack()
        tk.Scale(control_frame, from_=10, to=80, orient="horizontal", variable=parent.title_font_size,
                 command=lambda e: self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Max Width:").pack()
        tk.Scale(control_frame, from_=200, to=900, orient="horizontal", variable=parent.title_max_w,
                 command=lambda e: self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Title Max Height:").pack()
        tk.Scale(control_frame, from_=50, to=600, orient="horizontal", variable=parent.title_max_h,
                 command=lambda e: self.update_preview()).pack(fill="x")

        # Icon positioning sliders
        tk.Label(control_frame, text="TCB Icon X:").pack(pady=(20,0))
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.icon_x,
                 command=lambda e: self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="TCB Icon Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.icon_y,
                 command=lambda e: self.update_preview()).pack(fill="x")

        # Date positioning sliders
        tk.Label(control_frame, text="Date X:").pack(pady=(20,0))
        tk.Scale(control_frame, from_=0, to=1080, orient="horizontal", variable=parent.date_x,
                 command=lambda e: self.update_preview()).pack(fill="x")

        tk.Label(control_frame, text="Date Y:").pack()
        tk.Scale(control_frame, from_=0, to=1280, orient="horizontal", variable=parent.date_y,
                 command=lambda e: self.update_preview()).pack(fill="x")

        # Color picker for title
        color_btn = tk.Button(control_frame, text="Pick Title Color", command=self.pick_color)
        color_btn.pack(pady=10)

        # Preview canvas
        self.canvas = tk.Canvas(self, width=540, height=640, bg="black")
        self.canvas.pack(side="left", padx=10, pady=10)

        # Finalize button
        finalize_btn = tk.Button(self, text="Finalize & Prepare Articles", font=("Arial", 14), command=self.finalize)
        finalize_btn.pack(pady=5)

        self.parent = parent
        self.preview_img = None
        self.tk_preview_img = None

    def load_preview(self):
        self.update_preview()

    def update_preview(self):
        # Render image with current settings
        try:
            out_path, img = save_photocard(
                self.parent.title_text,
                self.parent.bg_image_path,
                TCB_ICON,
                FONT_PATH,
                (self.parent.title_x.get(), self.parent.title_y.get()),
                self.parent.title_font_size.get(),
                (self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                (self.parent.icon_x.get(), self.parent.icon_y.get()),
                (self.parent.date_x.get(), self.parent.date_y.get()),
                self.parent.title_color
            )
            self.preview_img = img.resize((540, 640), Image.ANTIALIAS)
            self.tk_preview_img = ImageTk.PhotoImage(self.preview_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_preview_img)
        except Exception as e:
            print(f"Preview update error: {e}")

    def pick_color(self):
        color_code = colorchooser.askcolor(title="Choose Title Color")
        if color_code and color_code[1]:
            rgb = color_code[0]
            self.parent.update_title_color((int(rgb[0]), int(rgb[1]), int(rgb[2]), 255))
            self.update_preview()

    def finalize(self):
        # Save final photocard with current settings and show step 4
        try:
            out_path, _ = save_photocard(
                self.parent.title_text,
                self.parent.bg_image_path,
                TCB_ICON,
                FONT_PATH,
                (self.parent.title_x.get(), self.parent.title_y.get()),
                self.parent.title_font_size.get(),
                (self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                (self.parent.icon_x.get(), self.parent.icon_y.get()),
                (self.parent.date_x.get(), self.parent.date_y.get()),
                self.parent.title_color
            )
            self.parent.final_image_path = out_path
            self.parent.show_frame(Step4Frame)
            self.parent.frames[Step4Frame].load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save final photocard: {e}")

# === Step 4 Frame: Final Output & Copy ===
class Step4Frame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        tk.Label(self, text="Photocard Created!", font=("Arial", 18)).pack(pady=10)

        self.path_label = tk.Label(self, text="", fg="blue", cursor="hand2")
        self.path_label.pack()
        self.path_label.bind("<Button-1>", self.open_folder)

        tk.Label(self, text="📝 Summary").pack(pady=(15,0))
        self.summary_box = ScrolledText(self, height=5, width=90)
        self.summary_box.pack(padx=10)

        self.copy_summary_btn = tk.Button(self, text="Copy Summary", command=self.copy_summary)
        self.copy_summary_btn.pack(pady=5)

        tk.Label(self, text="📄 Full Article + Source").pack(pady=(10,0))
        self.full_box = ScrolledText(self, height=10, width=90)
        self.full_box.pack(padx=10)

        self.copy_full_btn = tk.Button(self, text="Copy Full Article", command=self.copy_full)
        self.copy_full_btn.pack(pady=5)

        self.another_btn = tk.Button(self, text="Make Another Photocard", command=self.make_another)
        self.another_btn.pack(pady=20)

        self.parent = parent

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

        # Reset title customization vars
        self.parent.title_x.set(150)
        self.parent.title_y.set(880)
        self.parent.title_font_size.set(36)
        self.parent.title_max_w.set(700)
        self.parent.title_max_h.set(200)

        self.parent.icon_x.set(800)
        self.parent.icon_y.set(20)
        self.parent.date_x.set(800)
        self.parent.date_y.set(1240)

        self.parent.title_color = (255,255,255,255)

        self.parent.show_frame(Step1Frame)
        self.parent.frames[Step1Frame].bg_label.config(text="No image selected")
        self.parent.frames[Step1Frame].gen_button.config(state="disabled")

if __name__ == "__main__":
    app = TCBWizardApp()
    app.mainloop()
