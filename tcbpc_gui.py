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
import sys # Added for cross-platform file opening
import subprocess # Added for cross-platform file opening

# Download NLTK punkt tokenizer if not already present
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt', quiet=True)

# === Paths and constants ===
# Ensure these files exist in the same directory as your script
TEMPLATE_IMAGE = "tcb-template.png"
TCB_ICON = "tcb-icon.png"
FONT_PATH = "TiroBangla.ttf" # Make sure this font file exists
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Pictures")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

# Initialize summarization pipeline
# This can take some time, so it's initialized once globally.
try:
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
except Exception as e:
    print(f"Warning: Could not load summarization model. Summarization feature may not work: {e}")
    summarizer = None # Set to None if loading fails

# === Helper functions ===
def extract_article(url):
    article = Article(url, language='en')
    article.download()
    article.parse()
    return article.title.strip(), article.text.strip()

def summarize_article(text):
    if summarizer is None:
        return "Summarization model not loaded. Cannot summarize."

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

    summaries = []
    for chunk in chunks:
        if chunk.strip():
            try:
                # Ensure the chunk is not too long for the model
                # Some models have token limits (e.g., 1024 for distilbart)
                # This simple truncation prevents errors for very long chunks
                if len(chunk) > 1000: # Heuristic, adjust based on model's actual token limit
                    chunk = chunk[:1000]
                summaries.append(summarizer(chunk, max_length=80, min_length=20, do_sample=False)[0]['summary_text'])
            except Exception as e:
                print(f"Warning: Could not summarize chunk '{chunk[:50]}...': {e}")
                summaries.append(chunk) # Fallback to original chunk if summarization fails

    summary = " ".join(summaries)
    return summary.strip()

def draw_multicolor_text(draw, position, text, font, colors, max_width, max_height, line_spacing_add=0):
    words = text.split()
    lines = []
    line = ''
    
    # Calculate lines based on max_width
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

    # Calculate line height with spacing
    line_h = font.getbbox('A')[3] - font.getbbox('A')[1] + 4 + line_spacing_add
    total_h = line_h * len(lines)
    x, y = position
    start_y = y + max(0, (max_height - total_h)//2) # Center vertically within max_height

    # Create a flat color map for each character in the *reconstructed* text
    # This is crucial because `text.split()` and `join()` might alter space counts
    reconstructed_text = ' '.join(words) # Use this for character indexing
    color_map = [(255,255,255,255)] * len(reconstructed_text) # Default white

    # Apply colors from ranges to the color_map
    merged_colors = merge_color_ranges(colors)
    for s_idx, e_idx, col in merged_colors:
        # Ensure indices are within bounds of the reconstructed text
        for i in range(max(0, s_idx), min(len(reconstructed_text), e_idx)):
            if i < len(color_map):
                color_map[i] = col

    char_index_in_reconstructed_text = 0
    for line_content in lines:
        bbox = draw.textbbox((0,0), line_content, font=font)
        line_w = bbox[2] - bbox[0]
        cur_x = x + (max_width - line_w)//2 # Center alignment

        for ch in line_content:
            if char_index_in_reconstructed_text < len(color_map):
                c = color_map[char_index_in_reconstructed_text]
            else:
                c = (255,255,255,255) # Fallback to white if index out of bounds

            draw.text((cur_x, start_y), ch, font=font, fill=c)
            char_w = draw.textbbox((0,0), ch, font=font)[2] - draw.textbbox((0,0), ch, font=font)[0]
            cur_x += char_w
            
            # Increment index for the next character in the reconstructed text
            char_index_in_reconstructed_text += 1
            # If the next character in reconstructed_text is a space, increment again
            # to correctly map colors across word breaks. This is a heuristic.
            if char_index_in_reconstructed_text < len(reconstructed_text) and reconstructed_text[char_index_in_reconstructed_text] == ' ':
                char_index_in_reconstructed_text += 1

        start_y += line_h


def generate_photocard(title, bg_path, template_path, font_path, output_path,
                       title_pos, title_font_size, title_box, title_line_spacing, title_colors,
                       icon_pos, date_pos,
                       custom_text_content, custom_text_pos, custom_text_font_size, custom_text_box, custom_text_colors):
    try:
        bg = Image.open(bg_path).convert("RGBA")
        w_percent = 1080 / float(bg.size[0])
        h_size = int((float(bg.size[1]) * float(w_percent)))
        bg = bg.resize((1080, h_size), Image.LANCZOS)
    except FileNotFoundError:
        # Fallback if background image is not found (e.g., in preview mode before selection)
        bg = Image.new("RGBA", (1080, 1280), (50, 50, 50, 255)) # Dark gray placeholder
        print(f"Warning: Background image not found at {bg_path}. Using placeholder.")
    except Exception as e:
        print(f"Error loading background image {bg_path}: {e}. Using placeholder.")
        bg = Image.new("RGBA", (1080, 1280), (50, 50, 50, 255))


    overlay = Image.open(template_path).convert("RGBA")

    canvas_height = max(bg.size[1], overlay.size[1])
    canvas = Image.new("RGBA", (1080, canvas_height), (0,0,0,255))
    canvas.paste(bg, (0,0))
    canvas.alpha_composite(overlay, (0,0))

    draw = ImageDraw.Draw(canvas)

    if os.path.exists(TCB_ICON):
        icon = Image.open(TCB_ICON).convert("RGBA")
        canvas.paste(icon, icon_pos, icon)

    # Date Text
    try:
        date_font = ImageFont.truetype(font_path, 24)
    except IOError:
        print(f"Warning: Font file not found at {font_path}. Using default Pillow font for date.")
        date_font = ImageFont.load_default()
    date_str = datetime.datetime.now().strftime("%d %B, %Y").upper()
    draw.text(date_pos, date_str, font=date_font, fill=(255,255,255,255))

    # Draw Title Text
    if title.strip():
        try:
            font_title = ImageFont.truetype(font_path, title_font_size)
        except IOError:
            print(f"Warning: Font file not found at {font_path}. Using default Pillow font for title.")
            font_title = ImageFont.load_default()
        draw_multicolor_text(draw, title_pos, title, font_title, title_colors, title_box[0], title_box[1], line_spacing_add=title_line_spacing)

    # Draw Custom Text
    if custom_text_content.strip():
        try:
            font_custom = ImageFont.truetype(font_path, custom_text_font_size)
        except IOError:
            print(f"Warning: Font file not found at {font_path}. Using default Pillow font for custom text.")
            font_custom = ImageFont.load_default()
        draw_multicolor_text(draw, custom_text_pos, custom_text_content, font_custom, custom_text_colors, custom_text_box[0], custom_text_box[1], line_spacing_add=0)

    final_img = canvas.crop((0, 0, 1080, 1280))
    final_img.save(output_path)
    return output_path, final_img

def merge_color_ranges(ranges):
    if not ranges:
        return []
    
    # Sort by start index
    ranges.sort(key=lambda x: x[0])
    
    if not ranges:
        return []

    merged = []
    current_range = list(ranges[0]) # Convert to list to make it mutable

    for i in range(1, len(ranges)):
        next_start, next_end, next_color = ranges[i]
        
        # Check for overlap or adjacency with the same color
        if next_start <= current_range[1] and next_color == current_range[2]:
            current_range[1] = max(current_range[1], next_end)
        else:
            # No overlap with same color, or different color, so add current and start new
            merged.append(tuple(current_range))
            current_range = list(ranges[i])
            
    merged.append(tuple(current_range)) # Add the last range

    # One more pass to merge truly adjacent ranges of the same color that might have been split
    # due to intermediate different-colored ranges.
    final_merged = []
    if merged:
        final_merged.append(merged[0])
        for i in range(1, len(merged)):
            prev_start, prev_end, prev_color = final_merged[-1]
            curr_start, curr_end, curr_color = merged[i]
            
            # If current range starts exactly where previous ended AND colors are the same
            if curr_start == prev_end and curr_color == prev_color:
                final_merged[-1] = (prev_start, curr_end, prev_color) # Extend previous
            else:
                final_merged.append(merged[i]) # Add as new range

    return final_merged


# === The Wizard GUI App ===
class TCBWizardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TCB News Photocard Generator")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(True, True)
        self.state('zoomed')

        # --- Apply Dark Theme ---
        style = ttk.Style()
        style.theme_use('clam') # 'clam' is a good base for dark themes

        # Configure colors for various ttk widgets
        style.configure('.', background='#2E2E2E', foreground='#FFFFFF', borderwidth=0)
        style.configure('TFrame', background='#2E2E2E')
        style.configure('TLabel', background='#2E2E2E', foreground='#FFFFFF')
        style.configure('TButton', background='#4F4F4F', foreground='#FFFFFF', borderwidth=1, relief="raised")
        style.map('TButton', background=[('active', '#6E6E6E')])
        style.configure('TEntry', fieldbackground='#4F4F4F', foreground='#FFFFFF', borderwidth=1)
        style.configure('TScrolledText', background='#4F4F4F', foreground='#FFFFFF', insertbackground='#FFFFFF') # Custom for ScrolledText
        style.configure('TProgressbar', background='#007ACC', troughcolor='#4F4F4F')
        style.configure('Horizontal.TScale', background='#2E2E2E', troughcolor='#4F4F4F', sliderrelief='flat')
        style.configure('TLabelFrame', background='#2E2E2E', foreground='#FFFFFF', borderwidth=1)
        style.configure('TLabelframe.Label', background='#2E2E2E', foreground='#FFFFFF') # For the label inside Labelframe

        # For tk.Text, tk.Canvas, and tk.Label which don't directly use ttk styles
        self.option_add('*tearOff', False) # For consistent menu behavior
        self.option_add('*Text.background', '#4F4F4F')
        self.option_add('*Text.foreground', '#FFFFFF')
        self.option_add('*Text.insertBackground', '#FFFFFF')
        self.option_add('*Canvas.background', '#2E2E2E')
        self.option_add('*Label.background', '#2E2E2E')
        self.option_add('*Label.foreground', '#FFFFFF')
        self.option_add('*Button.background', '#4F4F4F')
        self.option_add('*Button.foreground', '#FFFFFF')


        self.news_url = tk.StringVar()
        self.bg_image_path = None

        self.title_text = ""
        self.summary_text = ""
        self.full_text = ""

        # Title text parameters
        self.title_x = tk.IntVar(value=150)
        self.title_y = tk.IntVar(value=880)
        self.title_font_size = tk.IntVar(value=36)
        self.title_max_w = tk.IntVar(value=700)
        self.title_max_h = tk.IntVar(value=200)
        self.title_line_spacing = tk.IntVar(value=4)
        self.title_colors = [(0, 10000, (255,255,255,255))] # Default white for full text length

        # TCB Icon parameters
        self.icon_x = tk.IntVar(value=800)
        self.icon_y = tk.IntVar(value=20)

        # Date parameters
        self.date_x = tk.IntVar(value=800)
        self.date_y = tk.IntVar(value=1240)

        # Custom text parameters
        self.custom_text = tk.StringVar(value="Add your custom message here!")
        self.custom_text_x = tk.IntVar(value=150)
        self.custom_text_y = tk.IntVar(value=500)
        self.custom_text_font_size = tk.IntVar(value=24)
        self.custom_text_max_w = tk.IntVar(value=700)
        self.custom_text_max_h = tk.IntVar(value=150)
        self.custom_text_colors = [(0, 10000, (255,255,255,255))] # Default white

        self.final_image_path = None

        self.frames = {}
        # Create a container frame to hold all step frames, allowing easy switching
        self.container = ttk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)

        for FrameClass in (Step1Frame, Step2Frame, Step3Frame, Step4Frame):
            # Pass self.container as master, and self (app) as parent_app
            frame = FrameClass(self.container, self) 
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
            # Call check_ready on the Step1Frame instance
            if Step1Frame in self.frames:
                self.frames[Step1Frame].bg_label.config(text=os.path.basename(path))
                self.frames[Step1Frame].check_ready() # Ensure check_ready is called

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
        if Step3Frame in self.frames:
            self.frames[Step3Frame].update_preview()

    def update_custom_text_colors(self, new_colors):
        self.custom_text_colors = new_colors
        if Step3Frame in self.frames:
            self.frames[Step3Frame].update_preview()

# === Base Frame Class - Removed and integrated relevant parts directly ===
# Each frame now inherits directly from ttk.Frame

# === Step 1 ===
class Step1Frame(ttk.Frame): # Changed to ttk.Frame
    def __init__(self, master_frame, parent_app):
        super().__init__(master_frame) # master_frame is now the container
        self.parent = parent_app # Keep parent for easier access to app variables

        # Main frame to contain all widgets for better layout management
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        url_label = ttk.Label(main_frame, text="Enter News Article URL:")
        url_label.pack(pady=(50, 5))

        self.url_entry = ttk.Entry(main_frame, textvariable=parent_app.news_url, width=80)
        self.url_entry.pack(pady=5)
        # Trace for news_url to enable/disable button
        self.parent.news_url.trace_add("write", self.check_ready)


        bg_label_frame = ttk.LabelFrame(main_frame, text="Background Image")
        bg_label_frame.pack(pady=20, padx=20, fill="x")

        self.bg_label = ttk.Label(bg_label_frame, text="No image selected")
        self.bg_label.pack(side="left", padx=10, pady=10)

        bg_button = ttk.Button(bg_label_frame, text="Browse", command=parent_app.choose_image)
        bg_button.pack(side="right", padx=10, pady=10)

        self.start_button = ttk.Button(main_frame, text="Start Processing", command=parent_app.start_generation, state=tk.DISABLED)
        self.start_button.pack(pady=30)

        # Initial call to set button state
        self.check_ready()

    def check_ready(self, *args):
        """Checks if both URL and BG image are provided and enables/disables the start button."""
        if self.parent.news_url.get() and self.parent.bg_image_path:
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)

# === Step 2 ===
class Step2Frame(ttk.Frame): # Changed to ttk.Frame
    def __init__(self, master_frame, parent_app):
        super().__init__(master_frame) # master_frame is now the container
        self.parent = parent_app

        label = ttk.Label(self, text="Extracting and Summarizing News...")
        label.pack(pady=20)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        self.status_label = ttk.Label(self, text="Starting...")
        self.status_label.pack(pady=5)

        # ScrolledText needs explicit dark background/foreground if not inheriting from ttk.Style
        self.summary_text_widget = ScrolledText(self, wrap=tk.WORD, height=10, bg='#4F4F4F', fg='#FFFFFF', insertbackground='#FFFFFF')
        self.summary_text_widget.pack(expand=True, fill="both", padx=20, pady=10)
        self.summary_text_widget.config(state=tk.DISABLED)

        self.continue_button = ttk.Button(self, text="Continue to Step 3", command=lambda: self.parent.show_frame(Step3Frame), state=tk.DISABLED)
        self.continue_button.pack(pady=20)

    def log(self, msg):
        self.summary_text_widget.config(state=tk.NORMAL)
        self.summary_text_widget.insert(tk.END, msg + "\n")
        self.summary_text_widget.see(tk.END)
        self.summary_text_widget.config(state=tk.DISABLED)
        self.update_idletasks() # Ensure GUI updates immediately

    def start_process(self, url, bg_path, app_instance):
        self.progress['value'] = 0
        self.status_label.config(text="Extracting article...")
        self.continue_button.config(state=tk.DISABLED)
        self.summary_text_widget.config(state=tk.NORMAL)
        self.summary_text_widget.delete(1.0, tk.END)
        self.summary_text_widget.config(state=tk.DISABLED)

        threading.Thread(target=self._process_article, args=(url, bg_path, app_instance), daemon=True).start()

    def _process_article(self, url, bg_path, app_instance):
        try:
            self.after(100, lambda: self.status_label.config(text="Extracting article..."))
            self.after(100, lambda: self.progress.config(value=25))
            title, text = extract_article(url)
            self.parent.title_text = title
            self.parent.full_text = text

            self.after(100, lambda: self.status_label.config(text="Summarizing article..."))
            self.after(100, lambda: self.progress.config(value=75))
            summary = summarize_article(text)
            self.parent.summary_text = summary

            self.after(100, lambda: self.summary_text_widget.config(state=tk.NORMAL))
            self.after(100, lambda: self.summary_text_widget.delete(1.0, tk.END))
            self.after(100, lambda: self.summary_text_widget.insert(tk.END, f"Title: {title}\n\nSummary:\n{summary}"))
            self.after(100, lambda: self.summary_text_widget.config(state=tk.DISABLED))

            self.after(100, lambda: self.progress.config(value=100))
            self.after(100, lambda: self.status_label.config(text="Processing complete!"))
            # Make sure Step3Frame is initialized before trying to load its preview
            self.after(100, lambda: self.parent.frames[Step3Frame].load_preview())
            self.after(100, lambda: self.continue_button.config(state=tk.NORMAL))

        except Exception as e:
            self.after(100, lambda: messagebox.showerror("Processing Error", f"Failed to process article: {e}"))
            self.after(100, lambda: self.status_label.config(text="Error occurred."))
            self.after(100, lambda: self.progress.config(value=0))
            self.after(100, lambda: self.continue_button.config(state=tk.DISABLED))

    def copy_summary(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.summary_text_widget.get("1.0", "end-1c"))
        messagebox.showinfo("Copied", "Summary copied to clipboard.")

    def copy_full(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.parent.full_text) # Access full_text from parent app
        messagebox.showinfo("Copied", "Full article copied to clipboard.")

# === Step 3 ===
class Step3Frame(ttk.Frame): # Changed to ttk.Frame
    def __init__(self, master_frame, parent_app):
        super().__init__(master_frame) # master_frame is now the container
        self.parent = parent_app
        self.current_preview_image = None
        
        self.canvas = tk.Canvas(self, bg="#2E2E2E") # Explicit dark background for tk.Canvas
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        control_panel = ttk.Frame(self, padding="10")
        control_panel.pack(side="right", fill="y")

        # Use a scrolled frame for many controls
        self.canvas_controls = tk.Canvas(control_panel, bg='#2E2E2E') # Explicit dark background
        self.scrollbar_controls = ttk.Scrollbar(control_panel, orient="vertical", command=self.canvas_controls.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas_controls)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_controls.configure(
                scrollregion=self.canvas_controls.bbox("all")
            )
        )

        self.canvas_controls.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_controls.configure(yscrollcommand=self.scrollbar_controls.set)

        self.canvas_controls.pack(side="left", fill="both", expand=True)
        self.scrollbar_controls.pack(side="right", fill="y")

        # --- Title Controls ---
        title_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Title Text Settings")
        title_controls_frame.pack(pady=10, fill="x", padx=5)

        self._create_slider(title_controls_frame, "X Pos:", self.parent.title_x, 0, 1080)
        self._create_slider(title_controls_frame, "Y Pos:", self.parent.title_y, 0, 1280)
        self._create_slider(title_controls_frame, "Font Size:", self.parent.title_font_size, 10, 100)
        self._create_slider(title_controls_frame, "Max Width:", self.parent.title_max_w, 100, 1000)
        self._create_slider(title_controls_frame, "Max Height:", self.parent.title_max_h, 50, 500)
        self._create_slider(title_controls_frame, "Line Spacing:", self.parent.title_line_spacing, 0, 20)

        title_color_button = ttk.Button(title_controls_frame, text="Set Title Colors", command=self.open_color_picker_title)
        title_color_button.pack(pady=5)

        # tk.Text needs explicit dark background/foreground
        self.title_text_widget = tk.Text(title_controls_frame, height=4, width=30, wrap="word", font=("TiroBangla", 14),
                                         bg='#4F4F4F', fg='#FFFFFF', insertbackground='#FFFFFF')
        self.title_text_widget.pack(fill="x", padx=5, pady=5)
        self.title_text_widget.bind("<KeyRelease>", self.on_title_text_change)
        # Force initial update for preview if title_text has initial value from URL
        self.title_text_widget.bind("<<Modified>>", self.on_title_text_change)


        # --- Custom Text Controls ---
        custom_text_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Custom Text Settings")
        custom_text_controls_frame.pack(pady=10, fill="x", padx=5)

        custom_text_entry_label = ttk.Label(custom_text_controls_frame, text="Custom Text:")
        custom_text_entry_label.pack(pady=2)

        # tk.Text needs explicit dark background/foreground
        self.custom_text_widget = tk.Text(custom_text_controls_frame, height=3, width=30, wrap="word", font=("TiroBangla", 14),
                                          bg='#4F4F4F', fg='#FFFFFF', insertbackground='#FFFFFF')
        self.custom_text_widget.insert(tk.END, self.parent.custom_text.get())
        self.custom_text_widget.pack(pady=2, fill="x", padx=5)
        self.custom_text_widget.bind("<KeyRelease>", self.on_custom_text_change)
        self.custom_text_widget.bind("<<Modified>>", self.on_custom_text_change)


        self._create_slider(custom_text_controls_frame, "X Pos:", self.parent.custom_text_x, 0, 1080)
        self._create_slider(custom_text_controls_frame, "Y Pos:", self.parent.custom_text_y, 0, 1280)
        self._create_slider(custom_text_controls_frame, "Font Size:", self.parent.custom_text_font_size, 10, 100)
        self._create_slider(custom_text_controls_frame, "Max Width:", self.parent.custom_text_max_w, 100, 1000)
        self._create_slider(custom_text_controls_frame, "Max Height:", self.parent.custom_text_max_h, 50, 500)

        custom_text_color_button = ttk.Button(custom_text_controls_frame, text="Set Custom Text Colors", command=self.open_color_picker_custom_text)
        custom_text_color_button.pack(pady=5)

        # --- Icon & Date Controls ---
        icon_date_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Icon & Date Settings")
        icon_date_controls_frame.pack(pady=10, fill="x", padx=5)

        self._create_slider(icon_date_controls_frame, "TCB Icon X:", self.parent.icon_x, 0, 1080)
        self._create_slider(icon_date_controls_frame, "TCB Icon Y:", self.parent.icon_y, 0, 1280)
        self._create_slider(icon_date_controls_frame, "Date X:", self.parent.date_x, 0, 1080)
        self._create_slider(icon_date_controls_frame, "Date Y:", self.parent.date_y, 0, 1280)

        # Finalize Button (placed outside scrollable frame for visibility)
        self.finalize_btn = ttk.Button(self, text="Finalize & Prepare summarized and full article", command=self.finalize)
        self.finalize_btn.pack(pady=10)

        self.update_preview() # Initial preview update

    def _create_slider(self, parent_frame, label_text, var, from_, to_):
        # This helper now automatically binds to update_preview
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="x", pady=2)

        label = ttk.Label(frame, text=label_text)
        label.pack(side="left", padx=5)

        slider = ttk.Scale(frame, from_=from_, to_=to_, orient="horizontal", variable=var, command=lambda v: self.update_preview())
        slider.pack(side="left", expand=True, fill="x", padx=5)

        value_label = ttk.Label(frame, textvariable=var)
        value_label.pack(side="right", padx=5)

    def on_title_text_change(self, event=None):
        # Update parent's title_text from widget, then trigger preview update
        current_text = self.title_text_widget.get("1.0", "end-1c")
        if self.parent.title_text != current_text: # Only update if text has actually changed
            self.parent.title_text = current_text
            self.update_preview()
        self.title_text_widget.edit_modified(False)


    def on_custom_text_change(self, event=None):
        # Update parent's custom_text from widget, then trigger preview update
        current_text = self.custom_text_widget.get("1.0", "end-1c")
        if self.parent.custom_text.get() != current_text: # Only update if text has actually changed
            self.parent.custom_text.set(current_text)
            self.update_preview()
        self.custom_text_widget.edit_modified(False)


    def clear_text_widget_tags(self, text_widget):
        for tag in text_widget.tag_names():
            if tag.startswith("color"):
                text_widget.tag_delete(tag)

    def apply_colors_to_text_widget(self, text_widget, color_list):
        self.clear_text_widget_tags(text_widget)
        # Apply specific colors from color_list
        for i, (start, end, color) in enumerate(color_list):
            tag_name = f"color{i}"
            r,g,b,a = color
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            start_idx = f"1.{start}"
            end_idx = f"1.{end}"
            try:
                text_widget.tag_add(tag_name, start_idx, end_idx)
                text_widget.tag_config(tag_name, foreground=hex_color)
            except tk.TclError:
                pass # Index might be out of bounds if text changed, ignore

    def _pick_color_for_selection(self, text_widget, current_colors, update_callback):
        try:
            start_idx_str = text_widget.index("sel.first")
            end_idx_str = text_widget.index("sel.last")
        except tk.TclError:
            messagebox.showinfo("No Selection", "Please select a portion of the text to color.")
            return

        # Get the current text content to ensure indices are correct
        current_text_content = text_widget.get("1.0", "end-1c")
        start_char_idx = int(start_idx_str.split('.')[1])
        end_char_idx = int(end_idx_str.split('.')[1])

        # Adjust end_char_idx if selection goes to end of line including newline
        if end_char_idx > len(current_text_content):
            end_char_idx = len(current_text_content)

        # Get initial color from the first range, or default to white
        initial_color_rgb = (255, 255, 255)
        if current_colors:
            # Find a color that covers the start of the selection, if any
            for s, e, c in current_colors:
                if s <= start_char_idx < e:
                    initial_color_rgb = (c[0], c[1], c[2])
                    break
            
        color_code = colorchooser.askcolor(initialcolor=initial_color_rgb, title="Choose color for selected text")[1]
        if not color_code: # User cancelled color picker
            return
        
        # Convert hex color to RGBA tuple (0-255)
        rgb_int = self.winfo_rgb(color_code) # Returns (R, G, B) as 16-bit ints (0-65535)
        rgba = (rgb_int[0]//256, rgb_int[1]//256, rgb_int[2]//256, 255)

        new_colors_temp = []
        # Process existing ranges: split or keep based on overlap with new selection
        for s,e,c in current_colors:
            # Case 1: Existing range is completely outside the new selection
            if e <= start_char_idx or s >= end_char_idx:
                new_colors_temp.append((s,e,c))
            # Case 2: Existing range partially overlaps on the left
            elif s < start_char_idx < e:
                new_colors_temp.append((s, start_char_idx, c))
                if e > end_char_idx: # Also partially overlaps on the right
                    new_colors_temp.append((end_char_idx, e, c))
            # Case 3: Existing range partially overlaps on the right (but not left)
            elif s < end_char_idx < e:
                new_colors_temp.append((end_char_idx, e, c))
            # Case 4: New selection completely covers or is covered by existing range (handled by splits)
            # No action needed here, as the new color will be added below.

        # Add the new color range
        new_colors_temp.append((start_char_idx, end_char_idx, rgba))

        # Merge the temporary ranges to simplify and combine adjacent same-colored segments
        final_colors = merge_color_ranges(new_colors_temp)
        update_callback(final_colors) # Update the parent's color list

        self.apply_colors_to_text_widget(text_widget, final_colors)
        self.update_preview()

    def open_color_picker_title(self):
        self._pick_color_for_selection(self.title_text_widget, self.parent.title_colors, self.parent.update_title_colors)

    def open_color_picker_custom_text(self):
        self._pick_color_for_selection(self.custom_text_widget, self.parent.custom_text_colors, self.parent.update_custom_text_colors)

    def load_preview(self):
        # Load title text and colors
        self.title_text_widget.delete("1.0", tk.END)
        self.title_text_widget.insert(tk.END, self.parent.title_text)
        self.apply_colors_to_text_widget(self.title_text_widget, self.parent.title_colors)

        # Load custom text and colors
        self.custom_text_widget.delete("1.0", tk.END)
        self.custom_text_widget.insert(tk.END, self.parent.custom_text.get())
        self.apply_colors_to_text_widget(self.custom_text_widget, self.parent.custom_text_colors)

        self.update_preview()

    def update_preview(self):
        try:
            temp_output_path = os.path.join(OUTPUT_DIR, "preview_temp.png")
            # Use a default image if no background is selected yet for preview
            bg_path_for_preview = self.parent.bg_image_path if self.parent.bg_image_path else TEMPLATE_IMAGE

            _, img_pil = generate_photocard(
                self.parent.title_text,
                bg_path_for_preview,
                TEMPLATE_IMAGE,
                FONT_PATH,
                temp_output_path,
                (self.parent.title_x.get(), self.parent.title_y.get()),
                self.parent.title_font_size.get(),
                (self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                self.parent.title_line_spacing.get(),
                self.parent.title_colors,
                (self.parent.icon_x.get(), self.parent.icon_y.get()),
                (self.parent.date_x.get(), self.parent.date_y.get()),
                self.parent.custom_text.get(),
                (self.parent.custom_text_x.get(), self.parent.custom_text_y.get()),
                self.parent.custom_text_font_size.get(),
                (self.parent.custom_text_max_w.get(), self.parent.custom_text_max_h.get()),
                self.parent.custom_text_colors
            )

            # Get actual canvas dimensions, or use defaults if not yet rendered
            canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 540
            canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 640

            # Resize the PIL image to fit the canvas while maintaining aspect ratio
            img_pil.thumbnail((canvas_w, canvas_h), Image.LANCZOS)
            self.tk_preview_img = ImageTk.PhotoImage(img_pil) # Keep reference!

            self.canvas.delete("all")
            self.canvas.create_image(canvas_w / 2, canvas_h / 2, image=self.tk_preview_img)
            # Update scrollregion if needed (though thumbnail makes it fit)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)

        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2,
                                    text=f"Preview Error:\n{e}", fill="red", font=("Arial", 12))
            print(f"Error updating preview: {e}")

    def finalize(self):
        filename = datetime.datetime.now().strftime("TCBPhotocard_%Y%m%d_%H%M%S.png")
        out_path = os.path.join(OUTPUT_DIR, filename)

        try:
            generate_photocard(
                self.parent.title_text,
                self.parent.bg_image_path,
                TEMPLATE_IMAGE,
                FONT_PATH,
                out_path,
                (self.parent.title_x.get(), self.parent.title_y.get()),
                self.parent.title_font_size.get(),
                (self.parent.title_max_w.get(), self.parent.title_max_h.get()),
                self.parent.title_line_spacing.get(),
                self.parent.title_colors,
                (self.parent.icon_x.get(), self.parent.icon_y.get()),
                (self.parent.date_x.get(), self.parent.date_y.get()),
                self.parent.custom_text.get(),
                (self.parent.custom_text_x.get(), self.parent.custom_text_y.get()),
                self.parent.custom_text_font_size.get(),
                (self.parent.custom_text_max_w.get(), self.parent.custom_text_max_h.get()),
                self.parent.custom_text_colors
            )
            self.parent.final_image_path = out_path
            # Pass the PIL image directly to Step4Frame
            final_img_pil = Image.open(out_path) # Reload the generated image for display
            self.parent.frames[Step4Frame].set_image(final_img_pil)
            self.parent.show_frame(Step4Frame)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save final photocard: {e}")
            print(f"Finalize Error: {e}")

# === Step 4 ===
class Step4Frame(ttk.Frame): # Changed to ttk.Frame
    def __init__(self, master_frame, parent_app):
        super().__init__(master_frame) # master_frame is now the container
        self.parent = parent_app
        self.img_tk = None # To hold the PhotoImage reference

        label = ttk.Label(self, text="Photocard Generated!")
        label.pack(pady=20)

        self.image_canvas = tk.Canvas(self, width=400, height=600, bg="#2E2E2E") # Explicit dark background
        self.image_canvas.pack(pady=10, expand=True)

        self.path_label = ttk.Label(self, text="", cursor="hand2") # Changed to ttk.Label
        self.path_label.pack(pady=5)
        self.path_label.bind("<Button-1>", self.open_image_location)

        self.open_button = ttk.Button(self, text="Open Image Location", command=self.open_image_location)
        self.open_button.pack(pady=5)

        self.share_button = ttk.Button(self, text="Share (Coming Soon)", state=tk.DISABLED)
        self.share_button.pack(pady=5)

        back_button = ttk.Button(self, text="Generate New", command=self.reset_app)
        back_button.pack(pady=20)

    def set_image(self, pil_image):
        # Get current canvas dimensions for dynamic resizing
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()

        # Provide fallback dimensions if canvas not yet rendered
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 600

        img_width, img_height = pil_image.size
        # Calculate ratio to fit image within canvas
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        resized_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        self.img_tk = ImageTk.PhotoImage(resized_image) # Keep reference!

        self.image_canvas.delete("all")
        self.image_canvas.create_image(canvas_width / 2, canvas_height / 2, image=self.img_tk)
        
        if self.parent.final_image_path:
            self.path_label.config(text=f"Saved to: {self.parent.final_image_path}")

    def open_image_location(self, event=None):
        if self.parent.final_image_path and os.path.exists(self.parent.final_image_path):
            try:
                folder_path = os.path.dirname(self.parent.final_image_path)
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_path])
                else: # Linux and other POSIX systems
                    subprocess.Popen(["xdg-open", folder_path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image location: {e}")
        else:
            messagebox.showinfo("Info", "No image has been saved yet.")

    def reset_app(self):
        # Reset all relevant parent app variables
        self.parent.news_url.set("")
        self.parent.bg_image_path = None
        self.parent.final_image_path = None
        self.parent.title_text = "" # Clear title text
        self.parent.summary_text = "" # Clear summary text
        self.parent.full_text = "" # Clear full text
        self.parent.title_colors = [(0, 10000, (255,255,255,255))]
        self.parent.custom_text.set("Add source and relocate")
        self.parent.custom_text_colors = [(0, 10000, (255,255,255,255))]
        
        # Show the first frame and ensure its state is reset
        self.parent.show_frame(Step1Frame)
        self.parent.frames[Step1Frame].bg_label.config(text="No image selected")
        self.parent.frames[Step1Frame].check_ready()


if __name__ == "__main__":
    app = TCBWizardApp()
    app.mainloop()