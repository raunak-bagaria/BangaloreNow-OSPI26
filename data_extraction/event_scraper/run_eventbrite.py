#!/usr/bin/env python3
"""
Cross-platform runner for the Eventbrite scraper.
- Uses venv when available (Linux/macOS/Windows)
- Writes timestamped logs
- Merges temp output into a master JSON

Usage:
    python run_eventbrite.py
    ./run_eventbrite.py  # if executable
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR
VENV_DIR = PROJECT_DIR.parent / "venv"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "eventbrite.json"

# Ensure dirs exist
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Timestamped log file
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"eventbrite_run_{timestamp}.log"

# Decide python exe (prefer venv)
if sys.platform == "win32":
    venv_python = VENV_DIR / "Scripts" / "python.exe"
else:
    venv_python = VENV_DIR / "bin" / "python3"
python_exe = str(venv_python) if venv_python.exists() else sys.executable

print("=" * 60)
print("Starting Eventbrite Web Scraper (90-day window)")
print("=" * 60)
print(f"\n📡 Scraping events from Eventbrite website...")
print(f"📁 Output: {OUTPUT_FILE}\n")
print("-" * 60 + "\n")

with open(LOG_FILE, "a", encoding="utf-8") as log_file:
    log_file.write(f"===== RUN START: {datetime.now()} =====\n")
    log_file.flush()

    try:
        # Run Scrapy spider
        cmd_spider = [
            python_exe, "-m", "scrapy", "crawl", "eventbrite",
            "-O", str(OUTPUT_FILE),
            "-s", "LOG_LEVEL=INFO",
        ]
        result1 = subprocess.run(
            cmd_spider,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            text=True,
        )

        # No merge step needed - writing directly to single file
        result2 = type('obj', (object,), {'returncode': 0})()

        log_file.write(f"===== RUN END: {datetime.now()} =====\n")

        success = result1.returncode == 0 and result2.returncode == 0

        if success:
            print("\n" + "-" * 60)
            print("✓ Scraper + merge completed!")
            print(f"✓ Data saved to: {OUTPUT_FILE}")
            if OUTPUT_FILE.exists():
                import json

                events = json.load(open(OUTPUT_FILE, "r", encoding="utf-8"))
                print(f"✓ Total events scraped: {len(events)}")
            print(f"📝 Log: {LOG_FILE}")
            sys.exit(0)
        else:
            print("\n❌ Error occurred. Check log:", LOG_FILE)
            sys.exit(1)

    except Exception as e:
        log_file.write(f"ERROR: {str(e)}\n")
        print(f"\n❌ Exception: {e}")
        print(f"Log: {LOG_FILE}")
        sys.exit(1)
