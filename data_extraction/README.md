# Bangalore Events Data Extraction

Automated web scraping system that extracts events from multiple sources in Bangalore and consolidates them into a unified JSON database.

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Linux/macOS Setup

**Option 1: Without Virtual Environment (Global Install)**
```bash
cd data_extraction
pip3 install -r requirements.txt
playwright install chromium
```

**Option 2: With Virtual Environment (Recommended)**
```bash
cd BangaloreNow  # Project root
python3 -m venv venv
source venv/bin/activate
pip install -r data_extraction/requirements.txt
playwright install chromium
```

### Windows Setup

**Option 1: Without Virtual Environment (Global Install)**
```cmd
cd data_extraction
pip install -r requirements.txt
playwright install chromium
```

**Option 2: With Virtual Environment (Recommended)**
```cmd
cd BangaloreNow  # Project root
python -m venv venv
venv\Scripts\activate
pip install -r data_extraction\requirements.txt
playwright install chromium
```

### Verify Installation
```bash
python3 -m scrapy version  # Linux/macOS
python -m scrapy version   # Windows
playwright --version
```

## Quick Start

### Linux/macOS

```bash
cd event_scraper

# Run the full pipeline end-to-end (recommended):
python3 run_pipeline.py

# Or run individual components:
python3 run_allevents.py       # Pull allevents.in listings -> data/allevents.json
python3 run_eventbrite.py      # Pull eventbrite.com listings -> data/eventbrite.json
python3 run_district.py        # Pull district.in listings -> data/district.json
python3 output_enhancer.py     # Clean & normalize all JSON -> cleaned_data/*_cleaned.json
python3 consolidate_events.py  # Merge all sources -> cleaned_data/events_master.json
python3 load_to_supabase.py    # Load to Supabase (geocode + upsert)
```

### Windows

```cmd
cd event_scraper

REM Run the full pipeline end-to-end (recommended):
python run_pipeline.py

REM Or run individual components:
python run_allevents.py       REM Pull allevents.in listings
python run_eventbrite.py      REM Pull eventbrite.com listings
python run_district.py        REM Pull district.in listings
python output_enhancer.py     REM Clean & normalize all JSON
python consolidate_events.py  REM Merge all sources
python load_to_supabase.py    REM Load to Supabase
```

**Note**: The scripts automatically detect and use virtual environment if present at `../venv/`. Otherwise, they use system Python.

## Execution Times

- **allevents.in scraper**: ~2-3 minutes (77 events across ~10 pages)
- **eventbrite.com scraper**: ~3-5 minutes (18 events across ~20 pages, Playwright rendering adds overhead)
- **district.in scraper**: ~10-20 minutes (155+ events with Playwright JavaScript rendering)
- **output_enhancer**: ~5-30 seconds (normalizes & enriches all events)
- **consolidation script**: ~5-10 seconds (merges & deduplicates)
- **Total end-to-end run**: ~15-30 minutes

*Times may vary based on network speed and system performance.*

## Data Files

```
event_scraper/
├── data/
│   ├── allevents.json       ← Raw: allevents.in events
│   ├── eventbrite.json      ← Raw: eventbrite.com events
│   └── district.json        ← Raw: district.in events
└── cleaned_data/
    ├── allevents_cleaned.json       ← Cleaned & normalized
    ├── eventbrite_cleaned.json      ← Cleaned & normalized
    ├── district_cleaned.json        ← Cleaned & normalized
    └── events_master.json           ← CONSOLIDATED: All sources deduplicated
```

## Architecture

### Data Sources (90-day window)
- **allevents.in** - Scrapy spider: [event_scraper/spiders/allevents.py](event_scraper/spiders/allevents.py)
- **eventbrite.com** - Scrapy spider with Playwright JS rendering: [event_scraper/spiders/eventbrite.py](event_scraper/spiders/eventbrite.py)
- **district.in** - Direct Playwright scraper (Zomato District): [zomato_district_scraper.py](event_scraper/zomato_district_scraper.py)

### Runners (Cross-platform: Linux/macOS/Windows)
- `run_allevents.py` - Execute allevents scraper
- `run_eventbrite.py` - Execute eventbrite scraper
- `run_district.py` - Execute district scraper
- `run_pipeline.py` - **Main orchestrator**: Runs all scrapers → enhancer → consolidation → load
- `consolidate_events.py` - Merge & deduplicate all sources into master

### Processors
- `output_enhancer.py` - Normalizes & enriches raw event data (detailed below)
- `load_to_supabase.py` - Geocodes & upserts events to Supabase

### Logs
All runs logged with timestamps: [event_scraper/logs/](event_scraper/logs/)

## Event Data Structure

```json
{
  "event_id": "unique_id",
  "event_key": "source:id",
  "event_name": "Event Title",
  "event_url": "https://...",
  "source": "allevents.in" | "eventbrite" | "district.in",
  "start_date": "2026-01-30",
  "start_time": "18:00",
  "end_date": "2026-01-30",
  "end_time": "20:00",
  "venue_name": "Venue Name",
  "venue_address": "Full Address",
  "resolved_venue_address": "Normalized Address (from output_enhancer)",
  "address_confidence": "high" | "medium" | "low",
  "organizer_name": "Organizer",
  "categories": "Business, Networking",
  "description": "Event description...",
  "ticket_price": "₹500" | "Free",
  "ticket_url": "https://...",
  "city": "Bangalore",
  "event_format": "Offline" | "Online" | "Hybrid",
  "source_url": "https://...",
  "last_updated": "2026-01-17T20:00:00.000000"
}
```

## Field Coverage (Master File: 95 events)

| Field | Coverage | Notes |
|-------|----------|-------|
| event_id | 100% | Always present |
| event_name | 100% | Always present |
| start_date | 100% | Always present |
| start_time | 100% | Always present |
| venue_address | 90% | Most events have address |
| venue_name | 81% | Most events have venue |
| end_date | 78% | When available on source |
| end_time | 78% | When available on source |
| categories | 45% | Varies by source |
| organizer_name | 34% | Not always listed |
| ticket_url | 32% | When tickets available |
| ticket_price | 25% | Often not disclosed |

## Sources Breakdown

- **allevents.in**: ~77 events
- **eventbrite.com**: ~18 events
- **district.in**: ~155+ events

**Date Range**: 90 days from current date

## Output Enhancer - Data Normalization

The `output_enhancer.py` script post-processes raw scraped JSON to normalize and enrich event data.

### What It Does

1. **Time Normalization** - Normalizes `start_time` / `end_time` into 24-hour format:
  - Handles strings like `5 PM`, `5:30 pm`, `9am`
  - Converts to `HH:MM` (e.g., `17:00`, `09:00`)
  - Strips common suffixes like `onwards`

2. **Venue Address Resolution** - Intelligently identifies and normalizes venue information:
   - Distinguishes between valid venue names (e.g., "Bangalore Tech Hub") and invalid placeholders (e.g., "venue", "TBA", "online")
   - Combines venue_name + venue_address + city into a coherent address
   - Removes duplicate city mentions (e.g., "Bangalore, Bangalore" → "Bangalore")
   - Flags confidence level based on address quality:
     - **high**: Contains street/building/postal info (e.g., "560034", "MG Road")
     - **medium**: Has partial address signals
     - **low**: Only city name or unclear venue

3. **Venue Heuristics** - Smart filtering to exclude:
   - Marketing jargon: "learn", "discover", "workshop", "training" (often misclassified venue names)
   - Invalid terms: "TBA", "to be announced", "N/A"
   - Unreasonably long strings (>80 chars) likely to be descriptions

4. **Address Signal Detection** - Recognizes valid address patterns:
   - Street numbers (3+ digits)
   - Common location words: road, street, nagar, layout, mall, campus, auditorium, park
   - Bangalore postal codes (560xxx)

5. **Output Fields Added**:
   - `resolved_venue_address`: Final normalized address
   - `address_confidence`: Quality indicator for geocoding systems

### Example Transformation

**Before (raw)**:
```json
{
  "venue_name": "Learn Data Science Workshop",
  "venue_address": "Bangalore",
  "city": "Bangalore"
}
```

**After (enhanced)**:
```json
{
  "venue_name": "Learn Data Science Workshop",
  "venue_address": "Bangalore",
  "city": "Bangalore",
  "resolved_venue_address": "Bangalore",
  "address_confidence": "low"
}
```

**Better example:**
```json
{
  "venue_name": "Microsoft India Office",
  "venue_address": "One Microsoft, Outer Ring Road, Devarabeesanahalli",
  "city": "Bangalore",
  "resolved_venue_address": "Microsoft India Office, One Microsoft, Outer Ring Road, Devarabeesanahalli, Bangalore",
  "address_confidence": "high"
}
```

### Usage

```bash
python3 output_enhancer.py
```

Processes the configured input files (`district.json`, `allevents.json`, `eventbrite.json`) from `data/`, and writes cleaned versions to `cleaned_data/` with `_cleaned.json` suffix.

## Dependencies

See Installation & Setup section above for detailed instructions.

**Core Dependencies:**
- scrapy >= 2.14.0
- scrapy-playwright >= 0.0.45
- playwright >= 1.57.0
- itemadapter >= 0.13.0
- python-dotenv >= 1.0.0
- pandas >= 2.0.0
- numpy >= 1.24.0

## Pipeline Flow Diagram

```
data/allevents.json
data/eventbrite.json    ──→ output_enhancer.py ──→ cleaned_data/*_cleaned.json
data/district.json                                          ↓
                                          consolidate_events.py
                                                     ↓
                                        cleaned_data/events_master.json
                                                     ↓
                                        load_to_supabase.py
                                                     ↓
                                          Supabase Database
```

## Notes

- **Deduplication**: Events merged by `event_key` (source:event_id)
- **Updates**: Each run overwrites source JSON files
- **Consolidation**: Run `consolidate_events.py` after scraping & enhancing to merge
- **Address Quality**: `address_confidence` helps filter events for geocoding
- **Logs**: All runs logged in `event_scraper/logs/` with timestamps

## Troubleshooting

**Playwright issues?**
```bash
playwright install chromium
```

**Python not found?**
- Ensure Python 3.8+ is installed: `python3 --version` (Linux/macOS) or `python --version` (Windows)
- Download from https://www.python.org/downloads/

**Permission denied (Linux/macOS)?**
```bash
chmod +x event_scraper/*.py
```

**Module not found?**
- If using venv: Ensure it's activated before running scripts
- If global: Reinstall dependencies with `pip install -r requirements.txt`

**Virtual environment not detected?**
- Venv must be at `../venv/` relative to event_scraper directory
- Or just use system Python (venv is optional)
