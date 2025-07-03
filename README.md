TCB Photocard Generator
This project provides a graphical user interface (GUI) application for generating "photocards" from news articles. It automates the process of extracting news content, summarizing it using a pre-trained AI model, and then overlaying the summary onto a customizable image template.

Installation
Follow these steps to set up and run the project in your development environment.

Prerequisites
Python 3.8 or higher. You can download it from python.org.

1. Clone the Repository
First, clone this repository to your local machine:

git clone <repository_url>
cd tcb-photocard-generator


2. Create and Activate a Virtual Environment
It's highly recommended to use a virtual environment to manage project dependencies:

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate


3. Install Dependencies
With your virtual environment activated, install the required Python packages:

pip install -r requirements.txt


The requirements.txt file should contain:

newspaper3k
transformers
Pillow
nltk


4. Download NLTK Data
The nltk library requires specific data models. Download the punkt tokenizer:

python -m nltk.downloader punkt


This will download the necessary data to your NLTK data directory (usually in your user's AppData\Roaming folder on Windows).

5. Pre-download Hugging Face Model (Optional but Recommended)
The distilbart-cnn-12-6 model is large and will be downloaded on the first run of the summarization code. To avoid delays during the first execution of the GUI, you can pre-download it:

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "sshleifer/distilbart-cnn-12-6"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print("Model and tokenizer downloaded successfully.")


Run these lines in a Python interpreter or a separate script. This will cache the model files, which PyInstaller can then bundle more reliably.

Usage
Running the Python Script
To run the application from its source code:

Ensure your virtual environment is activated.

Navigate to the project's root directory in your terminal.

Execute the main GUI script:

python tcbpc_gui.py


The GUI window will appear, allowing you to:

Step 1: Input News URL: Paste a news article URL into the provided field.

Step 2: Start Processing: Click the "Start Processing" button to extract, summarize, and generate the photocard.

Step 3: Save Photocard: Once processed, a "Save Photocard" button will appear, allowing you to save the generated image.

Features
News Article Extraction: Fetches content from a provided news URL.

AI-Powered Summarization: Utilizes the distilbart-cnn-12-6 model from Hugging Face's transformers library to create concise summaries of news articles.

Photocard Generation: Overlays the summarized text onto a customizable template image (tcb-template.png).

Customizable Icon and Font: Allows for branding with a custom application icon (tcb-icon.ico, tcb-icon.png) and text font (TiroBangla.ttf).

User-Friendly GUI: Built with tkinter for easy interaction.

Standalone Executable (Windows): Can be bundled into a single executable file for easy distribution.

Technologies Used
Python 3.x

Tkinter: For the graphical user interface.

newspaper3k: For news article extraction and parsing.

transformers (Hugging Face): For the distilbart-cnn-12-6 summarization model.

Pillow (PIL Fork): For image manipulation (overlaying text on the template).

NLTK: For text processing, specifically sentence tokenization (punkt tokenizer).

PyInstaller: For creating the standalone Windows executable.

Building the Executable (Windows)
You can create a single, standalone executable for Windows using PyInstaller.

Prerequisites for Building
Install PyInstaller in your virtual environment:

pip install pyinstaller


Building Steps
Clean Previous Builds: Before building, it's crucial to remove any leftover files from previous build attempts. Navigate to your project's root directory in PowerShell/CMD and run:

Remove-Item -Recurse -Force build
Remove-Item -Recurse -Force dist
Remove-Item tcbpc_gui.spec # Delete the .spec file if it exists


Run PyInstaller Command: Execute the following command. This command tells PyInstaller to create a single executable (--onefile), not open a console window (--noconsole), and include your data files and custom icon:

python -m PyInstaller --noconsole --onefile ^
--add-data "tcb-template.png;." ^
--add-data "tcb-icon.png;." ^
--add-data "TiroBangla.ttf;." ^
--add-data "C:\Users\YourUser\AppData\Roaming\nltk_data;nltk_data" ^
--icon="tcb-icon.ico" tcbpc_gui.py


Important:

Replace C:\Users\YourUser\AppData\Roaming\nltk_data with the actual path to your nltk_data directory (found in the "Download NLTK Data" section).

The ^ characters are for line continuation in PowerShell; on Linux/macOS, use \ instead.

Locate the Executable:
After a successful build, your executable (tcbpc_gui.exe) will be located in the dist folder:

D:\ProgDev\tcb-photocard-generator\dist\tcbpc_gui.exe

Troubleshooting Executable Issues
If the generated executable doesn't work as expected (e.g., crashes immediately or shows a generic error), try the following:

Run without --noconsole: Re-build the executable by removing the --noconsole flag from the PyInstaller command. Then, run the .exe from your command line (.\tcbpc_gui.exe in the dist folder). This will open a console window that should display any Python tracebacks or error messages, providing crucial debugging information.

Verify Data Paths: Ensure all --add-data paths are correct and that the destination paths (., nltk_data) are appropriate for how your application tries to access these files at runtime.

Antivirus Interference: Sometimes, antivirus software can quarantine or block parts of a PyInstaller-generated executable, especially large ones or those that unpack to temporary directories. Temporarily disable your antivirus or add an exception for the dist folder and the .exe to test if this is the cause.

Transformers Model Issues: If the error points to transformers not finding model files, ensure the model was fully downloaded in your development environment before building. For very persistent issues, you might need to manually copy the entire model cache into the bundled application using --add-data, though this is more complex.

Project Structure
tcb-photocard-generator/
├── .gitignore
├── requirements.txt
├── README.md
├── generate_news_photocard.py        # Core logic for photocard generation
├── generate_news_summary.py          # Core logic for news summarization (uses transformers)
├── generate_photocard.py             # (Likely a helper for image manipulation)
├── tcbpc_gui.py                      # Main GUI application script
├── tcbpc_primitive_gui.py            # (Possibly an older/simpler GUI version)
├── tcb-template.png                  # Image template for photocards
├── tcb-icon.png                      # Application icon (PNG format)
├── tcb-icon.ico                      # Application icon (ICO format for Windows executable)
└── TiroBangla.ttf                    # Custom font file


Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests.

License
This project is open-source and available under the MIT License.
