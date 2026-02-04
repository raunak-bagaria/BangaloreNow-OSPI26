#!/usr/bin/env python3
"""End-to-end pipeline runner for data_extraction.

Runs:
  1) Allevents spider -> data/allevents.json
  2) Eventbrite spider (Playwright) -> data/eventbrite.json
  3) District scraper (Playwright) -> data/district.json
  4) Output enhancer -> cleaned_data/*_cleaned.json
  5) Consolidation -> cleaned_data/events_master.json
  6) Load -> Supabase (geocode + upsert)

This is intended to be called from cron.

Usage:
  python3 run_pipeline.py
  python3 run_pipeline.py --skip-eventbrite   # useful for testing
  python3 run_pipeline.py --skip-load         # scrape only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-allevents", action="store_true")
    parser.add_argument("--skip-eventbrite", action="store_true")
    parser.add_argument("--skip-district", action="store_true")
    parser.add_argument("--skip-enhancer", action="store_true")
    parser.add_argument("--skip-consolidate", action="store_true")
    parser.add_argument("--skip-load", action="store_true")
    parser.add_argument("--skip-geocoding", action="store_true")
    args = parser.parse_args(argv)

    if not args.skip_allevents:
        _run([sys.executable, str(SCRIPT_DIR / "run_allevents.py")])

    if not args.skip_eventbrite:
        _run([sys.executable, str(SCRIPT_DIR / "run_eventbrite.py")])

    if not args.skip_district:
        _run([sys.executable, str(SCRIPT_DIR / "run_district.py")])

    if not args.skip_enhancer:
        _run([sys.executable, str(SCRIPT_DIR / "output_enhancer.py")])

    if not args.skip_consolidate:
        _run([sys.executable, str(SCRIPT_DIR / "consolidate_events.py")])

    if not args.skip_load:
        load_cmd = [sys.executable, str(SCRIPT_DIR / "load_to_supabase.py")]
        if args.skip_geocoding:
            load_cmd.append("--skip-geocoding")
        _run(load_cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
