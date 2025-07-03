
# TCB Photocard Generator 📰🖼️

A graphical user interface (GUI) tool that automates the creation of custom photocards from news articles. It extracts, summarizes, and overlays news content onto a photocard template using AI and customizable design settings.

## Installation

### Prerequisites

- Python 3.8 or higher

### 1. Clone the Repository

```bash
git clone <repository_url>
cd tcb-photocard-generator
```

### 2. Create and Activate a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
newspaper3k
transformers
Pillow
nltk
```

### 4. Download NLTK Data

```bash
python -m nltk.downloader punkt
```

### 5. (Optional) Pre-download Transformers Model

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "sshleifer/distilbart-cnn-12-6"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
```

---

## Usage

Run the app:

```bash
python tcbpc_gui.py
```

**Steps in GUI:**

1. Paste a news article URL.
2. Choose a background photo.
3. Click "Generate Photocard".
4. Customize, then finalize and save.

---

## Features

- **News Article Extraction**
- **AI Summarization (distilbart-cnn-12-6)**
- **Photocard Overlay on Template**
- **Color Picker for Title/Source Text**
- **Custom Font Support (TiroBangla.ttf)**
- **User-Friendly Multi-Step GUI**
- **Optional Windows Executable Support**

---

## Technologies

- Python 3.x
- tkinter
- newspaper3k
- transformers
- Pillow (PIL)
- NLTK
- PyInstaller (for .exe build)

---

## Build Executable (Windows)

### Prerequisites

```bash
pip install pyinstaller
```

### Clean Old Builds

```powershell
Remove-Item -Recurse -Force build
Remove-Item -Recurse -Force dist
Remove-Item tcbpc_gui.spec
```

### Run PyInstaller

```powershell
python -m PyInstaller --noconsole --onefile ^
--add-data "tcb-template.png;." ^
--add-data "tcb-icon.png;." ^
--add-data "TiroBangla.ttf;." ^
--add-data "C:\Users\YourUser\AppData\Roaming\nltk_data;nltk_data" ^
--icon="tcb-icon.ico" tcbpc_gui.py
```

> Replace paths accordingly. Use `\` instead of `^` on Linux/macOS.

### Output

```
dist/tcbpc_gui.exe
```

---

## Troubleshooting

- **Model not found**: ensure it's downloaded before building.
- **Crashes**: rebuild without `--noconsole` to see errors.
- **Antivirus**: may block executable, whitelist `dist/`.

---

## Project Structure

```
tcb-photocard-generator/
├── README.md
├── requirements.txt
├── tcbpc_gui.py
├── generate_news_summary.py
├── generate_news_photocard.py
├── generate_photocard.py
├── tcb-template.png
├── tcb-icon.png
├── tcb-icon.ico
└── TiroBangla.ttf
```

---

## License

MIT License

---

## Contributing

Pull requests and issues are welcome!
