#!/usr/bin/env python3
"""
Simple cross-platform scheduler to run Eventbrite scraper every 3 hours.
Press Ctrl+C to stop.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
RUNNER = SCRIPT_DIR / "run_eventbrite.py"
INTERVAL_SECONDS = 3 * 60 * 60  # 3 hours


def run_once():
    ts = datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] Running Eventbrite scrape...")
    result = subprocess.run([sys.executable, str(RUNNER)], cwd=SCRIPT_DIR)
    ts_done = datetime.now().isoformat(timespec="seconds")
    print(f"[{ts_done}] Finished with exit code {result.returncode}\n")
    return result.returncode


def main():
    try:
        while True:
            run_once()
            print(f"Sleeping for {INTERVAL_SECONDS/3600:.1f} hours...\n")
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
