#!/usr/bin/env python3
"""
Cross-platform Python script to run the event scraper.
Works on Linux, macOS, and Windows.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR
VENV_DIR = PROJECT_DIR.parent / "venv"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "allevents.json"

# Create directories
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Generate timestamp for log file
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"run_{timestamp}.log"

# Change to project directory
os.chdir(PROJECT_DIR)

# Determine the virtual environment activation and Python executable based on OS
if sys.platform == "win32":
    # Windows
    venv_python = VENV_DIR / "Scripts" / "python.exe"
    activate_script = VENV_DIR / "Scripts" / "activate.bat"
else:
    # Linux/macOS
    venv_python = VENV_DIR / "bin" / "python3"
    activate_script = VENV_DIR / "bin" / "activate"

# Use Python from venv or system Python if venv doesn't exist
python_exe = str(venv_python) if venv_python.exists() else sys.executable

# Open log file for appending
with open(LOG_FILE, "a", encoding="utf-8") as log_file:
    log_file.write(f"===== RUN START: {datetime.now()} =====\n")
    log_file.flush()
    
    try:
        # Run scrapy crawl directly to output file
        print("Running Scrapy spider...")
        result1 = subprocess.run(
            [python_exe, "-m", "scrapy", "crawl", "allevents", "-O", str(OUTPUT_FILE)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            text=True
        )
        
        result2 = type('obj', (object,), {'returncode': 0})()
        
        log_file.write(f"===== RUN END: {datetime.now()} =====\n")
        
        if result1.returncode == 0 and result2.returncode == 0:
            print(f"✅ Scraping completed successfully. Log: {LOG_FILE}")
            sys.exit(0)
        else:
            print(f"❌ Error occurred. Check log: {LOG_FILE}")
            sys.exit(1)
            
    except Exception as e:
        log_file.write(f"ERROR: {str(e)}\n")
        print(f"❌ Exception occurred: {e}")
        print(f"Check log: {LOG_FILE}")
        sys.exit(1)
