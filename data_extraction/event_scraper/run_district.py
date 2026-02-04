#!/usr/bin/env python3
"""
Cross-platform runner for the Zomato District (district.in) scraper.
Uses Playwright to scrape Bangalore events from the client-side rendered site.

Usage:
    python run_district.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR
VENV_DIR = PROJECT_DIR.parent / "venv"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "district.json"

LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"district_run_{timestamp}.log"

if sys.platform == "win32":
    venv_python = VENV_DIR / "Scripts" / "python.exe"
else:
    venv_python = VENV_DIR / "bin" / "python3"
python_exe = str(venv_python) if venv_python.exists() else sys.executable

print("=" * 60)
print("Zomato District (district.in) - Bangalore Events Scraper")
print("=" * 60)
print(f"\n📡 Scraping events from district.in (90-day window)...")
print(f"📁 Output: {OUTPUT_FILE}\n")
print("-" * 60 + "\n")

with open(LOG_FILE, "a", encoding="utf-8") as log_file:
    log_file.write(f"===== RUN START: {datetime.now()} =====\n")
    log_file.flush()

    try:
        from zomato_district_scraper import run_scraper
        import asyncio

        n = asyncio.run(run_scraper(OUTPUT_FILE, headless=True))
        log_file.write(f"Scraped {n} events\n")
        log_file.write(f"===== RUN END: {datetime.now()} =====\n")

        print("\n" + "-" * 60)
        print("✓ Scraper completed!")
        print(f"✓ Data saved to: {OUTPUT_FILE}")
        print(f"✓ Total events scraped: {n}")
        print(f"📝 Log: {LOG_FILE}")
        sys.exit(0)
    except Exception as e:
        log_file.write(f"ERROR: {str(e)}\n")
        import traceback
        log_file.write(traceback.format_exc())
        print(f"\n❌ Error: {e}")
        print(f"Log: {LOG_FILE}")
        sys.exit(1)
