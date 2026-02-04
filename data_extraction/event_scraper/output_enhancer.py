import json
from pathlib import Path
import re

# =====================
# CONFIG
# =====================

SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_DATA_DIR = SCRIPT_DIR / "cleaned_data"

INPUT_FILES = [
    "district.json",
    "allevents.json",
    "eventbrite.json",
]

# =====================
# TIME NORMALISERS
# =====================

def normalize_time(t):
    if not t or not isinstance(t, str):
        return t

    t = t.strip().lower()
    t = re.sub(r"\s*onwards", "", t)

    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t)
    if not match:
        return t

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    period = match.group(3)

    if period == "pm" and hour != 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute:02d}"

def normalize_event_times(event):
    for key in ["start_time", "end_time"]:
        event[key] = normalize_time(event.get(key))
    return event

# =====================
# VENUE HELPERS
# =====================

ADDRESS_SIGNAL_REGEX = re.compile(
    r"(\d{3,}|road|rd|street|st|nagar|layout|main|mall|campus|auditorium|park|grounds|560\d{3})",
    re.IGNORECASE
)

MARKETING_WORDS = [
    "learn", "discover", "build", "explore", "experience",
    "workshop", "training", "session", "masterclass"
]

INVALID_VENUE_NAMES = {
    "venue",
    "location",
    "tba",
    "to be announced",
    "online",
    "na",
    "n/a"
}

CITY_VARIANTS = {"bangalore", "bengaluru"}

# =====================
# VENUE HEURISTICS
# =====================

def looks_like_address(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    if len(text) > 140:
        return False
    return bool(ADDRESS_SIGNAL_REGEX.search(text.lower()))

def looks_like_venue_name(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False

    t = text.strip().lower()

    if t in INVALID_VENUE_NAMES:
        return False

    if len(t) > 80:
        return False

    for w in MARKETING_WORDS:
        if w in t:
            return False

    return True

def build_venue_candidates(event):
    candidates = []

    raw_addr = event.get("venue_address")
    venue_name = event.get("venue_name")
    city = event.get("city")

    if raw_addr:
        candidates.append(raw_addr)

    if looks_like_venue_name(venue_name):
        if city:
            candidates.append(f"{venue_name}, {city}")
        else:
            candidates.append(venue_name)

    if city:
        candidates.append(city)

    return candidates

# =====================
# DEDUPE + CONFIDENCE
# =====================

def dedupe_city(address: str, city: str) -> str:
    if not address or not city:
        return address

    parts = [p.strip() for p in address.split(",") if p.strip()]
    cleaned = []

    for p in parts:
        if p.lower() in CITY_VARIANTS:
            continue
        cleaned.append(p)

    cleaned.append(city)
    return ", ".join(cleaned)

def get_address_confidence(address: str, city: str) -> str:
    if not address:
        return "low"

    a = address.lower().strip()
    if city and a == city.lower():
        return "low"

    if ADDRESS_SIGNAL_REGEX.search(a):
        return "high"

    return "medium"

# =====================
# EVENT NORMALISATION
# =====================

def normalize_event_address(event):
    candidates = build_venue_candidates(event)
    city = event.get("city")

    for c in candidates:
        if looks_like_address(c) or looks_like_venue_name(c):
            final = dedupe_city(c.strip(), city)
            event["resolved_venue_address"] = final
            event["address_confidence"] = get_address_confidence(final, city)
            return event

    # Fallback: city only
    event["resolved_venue_address"] = city
    event["address_confidence"] = "low"
    return event

# =====================
# IO
# =====================

def load_events(filename):
    path = INPUT_DATA_DIR / filename
    if not path.exists():
        print(f"Missing input: {path} (skipping)")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_events(filename, events):
    out_name = filename.replace(".json", "_cleaned.json")
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DATA_DIR / out_name, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

# =====================
# MAIN
# =====================

def main():
    for file in INPUT_FILES:
        print(f"📥 Loading {file}")
        events = load_events(file)
        print(f"   → {len(events)} events")

        events = [
            normalize_event_address(
                normalize_event_times(e)
            )
            for e in events
        ]

        save_events(file, events)

    print("✅ Enhancer pipeline wired")

if __name__ == "__main__":
    main()
