#!/usr/bin/env python3
"""
Merge all event sources (allevents.in, eventbrite.com) into one master JSON.
Each event retains its 'source' field indicating the source website.
Deduplicates by event_key.
"""

import json
import os
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"

ALLEVENTS_FILE = DATA_DIR / "allevents.json"
EVENTBRITE_FILE = DATA_DIR / "eventbrite.json"
MASTER_FILE = DATA_DIR / "events_master.json"


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("CONSOLIDATING ALL EVENT SOURCES")
    print("=" * 60)

    # Load both sources
    allevents_data = load_json(ALLEVENTS_FILE)
    eventbrite_data = load_json(EVENTBRITE_FILE)

    print(f"\n📥 Loaded:")
    print(f"   - allevents.in: {len(allevents_data)} events")
    print(f"   - eventbrite.com: {len(eventbrite_data)} events")

    # Check for duplicates within each source as a fallback
    def check_duplicates_in_source(data, source_name):
        seen = set()
        duplicates = []
        for event in data:
            key = event.get("event_key")
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate(s) in {source_name}:")
            for dup in duplicates[:5]:  # Show first 5
                print(f"     - {dup}")
            if len(duplicates) > 5:
                print(f"     ... and {len(duplicates) - 5} more")
        return duplicates

    allevents_dups = check_duplicates_in_source(allevents_data, "allevents.in")
    eventbrite_dups = check_duplicates_in_source(eventbrite_data, "eventbrite.com")

    # Deduplicate by event_key
    combined_map = {}

    for event in allevents_data:
        key = event.get("event_key")
        if key:
            combined_map[key] = event

    for event in eventbrite_data:
        key = event.get("event_key")
        if key:
            combined_map[key] = event

    combined_events = list(combined_map.values())

    # Sort by start_date
    combined_events.sort(key=lambda e: e.get("start_date", ""), reverse=False)

    # Update timestamp
    for event in combined_events:
        event["last_updated"] = datetime.utcnow().isoformat()

    save_json(MASTER_FILE, combined_events)

    print(f"\n✅ Consolidation complete:")
    print(f"   - Total unique events: {len(combined_events)}")
    print(f"   - allevents.in: {sum(1 for e in combined_events if 'allevents' in e.get('source', ''))}")
    print(f"   - eventbrite.com: {sum(1 for e in combined_events if 'eventbrite' in e.get('source', ''))}")
    print(f"\n📁 Output: {MASTER_FILE}")

    # Print statistics
    print("\n" + "=" * 60)
    print("FIELD COVERAGE ACROSS ALL EVENTS")
    print("=" * 60)

    fields_count = {}
    for event in combined_events:
        for key, value in event.items():
            if value:
                fields_count[key] = fields_count.get(key, 0) + 1

    for key in sorted(fields_count.keys()):
        count = fields_count[key]
        pct = (100 * count) // len(combined_events)
        print(f"  {key}: {count}/{len(combined_events)} ({pct}%)")


if __name__ == "__main__":
    main()
