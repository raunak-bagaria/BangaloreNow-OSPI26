#!/usr/bin/env python3
"""
Zomato District (district.in) event scraper using Playwright.

Strategy (in order):
1. Network interception: Capture JSON from get_discovery_results, jumbo.edition.in, mpc events APIs
2. DOM listing: Select Bangalore via location modal, extract event links, scroll for pagination
3. Sitemap XML fallback: Fetch event-detail-pages.xml, filter URLs by bangalore/bengaluru
4. Event page DOM: Visit each event URL, parse details (no JSON-LD on District)

- Respects robots.txt: /events/ allowed; Disallow /*? so no query params
- Bangalore filter: venue/address/URL contains Bangalore, Bengaluru, BLR
- 90-day window, same fields as eventbrite/allevents for consolidation

Usage:
    python zomato_district_scraper.py [--output district.json] [--headless]
"""

import json
import re
import asyncio
import argparse
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Bangalore detection patterns (case-insensitive)
BANGALORE_PATTERNS = [
    r"\bbangalore\b",
    r"\bbengaluru\b",
    r"\bblr\b",
    r"\bkarnataka\b",  # Events in Karnataka are typically Bangalore area
]

# Fields matching EventItem from items.py
EVENT_FIELDS = [
    "event_id", "event_name", "event_url", "ticket_url", "ticket_price",
    "description", "categories", "start_date", "start_time", "end_date", "end_time",
    "venue_name", "venue_address", "event_format", "organizer_name", "city", "source",
    "source_url", "last_updated", "event_key",
]

MAX_DAYS_AHEAD = 90
BASE_URL = "https://www.district.in"
EVENTS_URL = "https://www.district.in/events/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
REQUEST_DELAY = 1.0  # Be respectful
TOTAL_TIMEOUT_SECONDS = None  # No timeout - let it take its time
PAGE_LOAD_TIMEOUT = 12000  # ms; avoid networkidle which can hang on SPAs
STALE_DAYS = 7  # Re-scrape events older than this to detect changes


def _is_bangalore(text: str | None) -> bool:
    """Quick check if text indicates Bangalore/Bengaluru location."""
    if not text:
        return False
    t = text.lower().strip()
    for pat in BANGALORE_PATTERNS:
        if re.search(pat, t, re.I):
            return True
    return False


def _safe_get(obj: dict, *keys, default=None):
    """Safely get nested dict key."""
    for k in keys:
        if obj is None:
            return default
        obj = obj.get(k) if isinstance(obj, dict) else None
    return obj if obj is not None else default


def _parse_date_display(raw: str | None) -> tuple[str | None, str | None]:
    """Parse 'Fri, 13 Feb, 5:00 PM' or 'Sat, 29 Nov 2025 - Sat, 13 Dec 2025' into (date, time)."""
    if not raw or not raw.strip():
        return None, None
    raw = raw.strip()
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    # Try "29 Nov 2025" or "29 Nov, 2025" (4-digit year)
    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(\d{4})?\s*[-–]?\s*(\d{1,2}:\d{2}\s*[AP]M)?", raw, re.I)
    if m:
        day, month_abbr, year_str, time_part = m.group(1), m.group(2), m.group(3), m.group(4)
        year = int(year_str) if year_str else datetime.now().year
        try:
            mo = month_map.get(month_abbr.lower()[:3], 1)
            dt = datetime(year, mo, int(day))
            start_date = dt.strftime("%Y-%m-%d")
            start_time = None
            if time_part:
                start_time = time_part.strip().replace(" ", "")[:5]
                if ":" in start_time:
                    start_time = start_time[:5]
            return start_date, start_time
        except Exception:
            pass
    # Try "Fri, 13 Feb, 5:00 PM" (no year)
    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(\d{1,2}:\d{2}\s*[AP]M)?", raw, re.I)
    if m:
        day, month_abbr, time_part = m.group(1), m.group(2), m.group(3)
        year = datetime.now().year
        try:
            mo = month_map.get(month_abbr.lower()[:3], 1)
            dt = datetime(year, mo, int(day))
            if dt < datetime.now():
                dt = datetime(year + 1, mo, int(day))
            start_date = dt.strftime("%Y-%m-%d")
            start_time = None
            if time_part:
                start_time = time_part.strip().replace(" ", "")[:5]
            return start_date, start_time
        except Exception:
            pass
    return None, None


def _build_event_item(
    event_id: str | None,
    event_name: str | None,
    event_url: str,
    ticket_url: str | None,
    ticket_price: str | None,
    description: str | None,
    categories: str | None,
    start_date: str | None,
    start_time: str | None,
    end_date: str | None,
    end_time: str | None,
    venue_name: str | None,
    venue_address: str | None,
    organizer_name: str | None,
) -> dict:
    """Build event dict with all fields, fallbacks for missing values."""
    ticket_url = ticket_url or event_url
    event_key = f"district:{event_id}" if event_id else f"district:url:{hash(event_url)}"
    return {
        "event_id": event_id,
        "event_name": event_name,
        "event_url": event_url,
        "ticket_url": ticket_url,
        "ticket_price": ticket_price,
        "description": description,
        "categories": categories,
        "start_date": start_date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "venue_name": venue_name,
        "venue_address": venue_address,
        "event_format": "In-person",  # District events are physical venue events
        "organizer_name": organizer_name,
        "city": "Bangalore",
        "source": "district.in",
        "source_url": event_url,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "event_key": event_key,
    }


def _fetch_bangalore_urls_from_sitemap() -> list[str]:
    """Fetch sitemap and return Bangalore event URLs (all <loc> that contain bangalore|bengaluru)."""
    urls = []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    bangalore_re = re.compile(r"\b(bangalore|bengaluru)\b", re.I)

    def collect_from_tree(tree):
        root = tree.getroot()
        for elem in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            if elem.text:
                loc = elem.text.strip()
                if bangalore_re.search(loc) and "/events/" in loc and "buy-tickets" in loc:
                    urls.append(loc)
        for elem in root.iter("loc"):
            if elem.text and elem.tag.endswith("loc"):
                loc = elem.text.strip()
                if bangalore_re.search(loc) and "/events/" in loc and "buy-tickets" in loc:
                    urls.append(loc)

    try:
        req = urllib.request.Request(
            "https://www.district.in/events/search-sitemap/sitemap-events.xml",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=15) as idx:
            tree = ET.parse(idx)
        collect_from_tree(tree)
        # If first file is an index (sitemap of sitemaps), follow first loc and collect from there
        root = tree.getroot()
        first_loc = root.find(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if first_loc is not None and first_loc.text and len(urls) == 0:
            detail_url = first_loc.text.strip()
            if "sitemap" in detail_url.lower():
                req2 = urllib.request.Request(detail_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req2, timeout=30) as resp:
                    detail_tree = ET.parse(resp)
                collect_from_tree(detail_tree)
    except Exception as e:
        pass  # Sitemap is best-effort; continue with DOM scraping
    return list(dict.fromkeys(urls))[:200]


def _in_date_range(start_date: str | None, max_days: int = MAX_DAYS_AHEAD) -> bool:
    if not start_date:
        return True
    try:
        dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        return datetime.now().date() <= dt <= (datetime.now().date() + timedelta(days=max_days))
    except Exception:
        return True


def _is_stale(event_dict: dict) -> bool:
    """True if event's last_updated is older than STALE_DAYS (re-scrape to detect changes)."""
    raw = event_dict.get("last_updated")
    if not raw:
        return True
    try:
        # Support ISO format with or without Z
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw.replace("+00:00", ""))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt).days
        return age_days >= STALE_DAYS
    except Exception:
        return True


async def _extract_from_api_captures(captured: list[dict]) -> list[dict]:
    """Try to extract event list from captured API JSON responses."""
    events = []
    for data in captured:
        if not isinstance(data, dict):
            continue
        # Various possible shapes from District APIs
        items = _safe_get(data, "data", "events") or _safe_get(data, "events") or _safe_get(data, "data") or []
        if isinstance(items, dict):
            items = items.get("items", items.get("events", []))
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            # Check if Bangalore
            venue = _safe_get(item, "venue", "name") or _safe_get(item, "venue_name") or ""
            city = _safe_get(item, "venue", "city") or _safe_get(item, "city") or _safe_get(item, "location", "city") or ""
            addr = _safe_get(item, "venue", "address") or _safe_get(item, "venue_address") or _safe_get(item, "address") or ""
            combined = f"{venue} {city} {addr}"
            if not _is_bangalore(combined):
                continue
            eid = _safe_get(item, "id") or _safe_get(item, "event_id")
            if eid is not None:
                eid = str(eid)
            name = _safe_get(item, "name") or _safe_get(item, "title") or _safe_get(item, "event_name")
            slug = _safe_get(item, "slug") or _safe_get(item, "url_slug")
            url = _safe_get(item, "url") or _safe_get(item, "event_url")
            if not url and slug:
                url = f"{BASE_URL}/events/{slug}" if "/events/" not in str(slug) else urljoin(BASE_URL, slug)
            if not url:
                continue
            price = _safe_get(item, "price", "display") or _safe_get(item, "min_price") or _safe_get(item, "ticket_price")
            if price is not None:
                price = str(price)
            start_dt = _safe_get(item, "start_date") or _safe_get(item, "start") or _safe_get(item, "date")
            start_date, start_time = None, None
            if isinstance(start_dt, str) and "T" in start_dt:
                parts = start_dt.split("T")
                start_date = parts[0][:10]
                start_time = parts[1][:5] if len(parts) > 1 else None
            elif isinstance(start_dt, str):
                start_date = start_dt[:10]
            desc = _safe_get(item, "description") or _safe_get(item, "about")
            cat = _safe_get(item, "category") or _safe_get(item, "categories")
            if isinstance(cat, list):
                cat = ", ".join(str(c) for c in cat)
            ev = _build_event_item(
                event_id=eid,
                event_name=name,
                event_url=url,
                ticket_url=url,
                ticket_price=price,
                description=desc,
                categories=cat,
                start_date=start_date,
                start_time=start_time,
                end_date=None,
                end_time=None,
                venue_name=venue or _safe_get(item, "venue_name"),
                venue_address=addr or _safe_get(item, "venue_address"),
                organizer_name=_safe_get(item, "organizer", "name") or _safe_get(item, "organizer_name"),
            )
            if _in_date_range(ev["start_date"]):
                events.append(ev)
    return events


async def _select_bangalore(page) -> bool:
    """Select Bangalore from location modal: click location -> type Bangalore/Bengaluru -> click city option."""
    try:
        # Click anything that opens the location modal (Select Location, or city name like Gurugram)
        loc_selectors = [
            'button:has-text("Select Location")',
            '[class*="location"]:has-text("Select Location")',
            'a:has-text("Select Location")',
            'button:has-text("Gurugram")',
            'button:has-text("Delhi")',
            'button:has-text("Mumbai")',
        ]
        clicked = False
        for sel in loc_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=4000)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            return False
        await asyncio.sleep(1.5)
        # Search input (placeholder often "Search for events, movies...")
        search_sel = page.locator('input[type="text"]').filter(has=page.locator("xpath=..")).first
        if await search_sel.count() == 0:
            search_sel = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first
        await search_sel.fill("Bangalore", timeout=3000)
        await asyncio.sleep(1.5)
        # Click city option: try "Bangalore, Karnataka" then "Bengaluru, Karnataka"
        for label in ["Bangalore, Karnataka", "Bengaluru, Karnataka", "Bangalore", "Bengaluru"]:
            try:
                opt = page.locator(f'button:has-text("{label}"), [role="option"]:has-text("{label}"), a:has-text("{label}")').first
                if await opt.count() and await opt.is_visible():
                    await opt.click(timeout=4000)
                    await asyncio.sleep(2)
                    return True
            except Exception:
                continue
        return False
    except Exception:
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def _collect_event_links_from_listing(page) -> list[str]:
    """Extract event URLs from the events listing page."""
    links = []
    try:
        # Event cards link to /events/something-buy-tickets
        anchors = page.locator('a[href*="/events/"][href*="buy-tickets"]')
        count = await anchors.count()
        for i in range(min(count, 150)):
            href = await anchors.nth(i).get_attribute("href")
            if href:
                full = urljoin(BASE_URL, href)
                if full not in links:
                    links.append(full)
    except Exception:
        pass
    return links


async def _scrape_event_page(page, url: str, seen: set, debug: bool = False) -> dict | None:
    """Visit single event page and extract details. Returns None if not Bangalore or duplicate."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_load_state("load", timeout=12000)
    except PlaywrightTimeout:
        pass
    except Exception as e:
        if debug:
            print(f"    [debug] goto failed: {e}")
        return None
    # Wait for SPA to render (content often appears after 1–8s; poll for h1)
    for poll_i in range(25):  # up to 25s
        await asyncio.sleep(1)
        try:
            h1_el = page.locator("h1").first
            n = await h1_el.count()
            if n:
                txt = await h1_el.text_content()
                if txt and txt.strip():
                    break
        except Exception:
            pass
    else:
        if debug:
            print(f"    [debug] no h1 after 25s: {url[:60]}...")
        return None
    await asyncio.sleep(0.3)

    await asyncio.sleep(REQUEST_DELAY)

    async def _text(sel: str) -> str | None:
        try:
            el = page.locator(sel).first
            if await el.count():
                t = await el.text_content()
                return t.strip() if t else None
        except Exception:
            pass
        return None

    event_name = await _text("h1")
    if not event_name:
        event_name = await _text("h2")
    if not event_name:
        # Some pages use a different heading structure
        try:
            for sel in ["[class*='event'] h1", "[class*='title']", "main h1"]:
                event_name = await _text(sel)
                if event_name and len(event_name) > 2:
                    break
        except Exception:
            pass
    if not event_name:
        if debug:
            print(f"    [debug] h1 empty: {url[:50]}...")
        return None

    # Venue: try "Venue" section, then "Get Directions" context, then any text with Bengaluru/Bangalore
    venue_block = page.locator("text=Venue").locator("..").locator("..")
    venue_name = None
    venue_address = None
    try:
        if await venue_block.count():
            paras = await venue_block.locator("p").all_text_contents()
            if paras:
                venue_name = paras[0].strip() if paras else None
                venue_address = ", ".join(p.strip() for p in paras[1:] if p.strip()) if len(paras) > 1 else None
    except Exception:
        pass
    if not venue_name:
        venue_name = await _text('[class*="venue"]')
    if not venue_name:
        # "Get Directions" is often next to venue name
        gd = page.locator('a:has-text("Get Directions"), button:has-text("Get Directions")').first
        if await gd.count():
            try:
                parent = gd.locator("xpath=../..")
                venue_name = await parent.locator("p, span, div").first.text_content()
                if venue_name:
                    venue_name = venue_name.strip()[:200]
            except Exception:
                pass
    # Venue paras may include "Get Directions" as last item - don't use as address
    if venue_address and "Get Directions" in (venue_address or ""):
        venue_address = venue_address.replace("Get Directions", "").strip().rstrip(",")
    if not venue_address:
        venue_address = await _text('[class*="address"]')
    if not venue_address:
        # Try text that looks like address (long, has comma/digits)
        for sel in ['p:has-text("India"), p:has-text("Karnataka")', '[class*="address"]']:
            venue_address = await _text(sel)
            if venue_address and len(venue_address) > 10:
                break

    combined_loc = f"{venue_name or ''} {venue_address or ''}"
    if not _is_bangalore(combined_loc) and not _is_bangalore(url):
        if debug:
            print(f"    [debug] not Bangalore: {combined_loc[:50]}...")
        return None

    # Extract event ID from URL
    slug_match = re.search(r"/events/([^/]+)-buy-tickets", url)
    event_id = slug_match.group(1) if slug_match else None

    # Date: try PM/AM first, then any text with month name (Jan, Feb, ... Nov 2025)
    date_text = None
    date_el = page.locator('p:has-text("PM"), p:has-text("AM")').first
    if await date_el.count():
        date_text = await date_el.text_content()
    if not date_text:
        for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]:
            el = page.locator(f'text=/{month}[a-z]*\\s+\\d{{1,2}}/').first
            if await el.count():
                date_text = await el.text_content()
                break
    start_date, start_time = _parse_date_display(date_text)

    # Price
    price_el = page.locator('text=₹').first
    ticket_price = None
    if await price_el.count():
        parent = price_el.locator("..")
        ticket_price = await parent.text_content()
        if ticket_price:
            ticket_price = ticket_price.strip()

    # Category
    cat_el = page.locator('p:has-text("Nightlife"), p:has-text("Comedy"), p:has-text("Music")').first
    categories = await cat_el.text_content() if await cat_el.count() else None
    if categories:
        categories = categories.strip()

    # Description
    about = page.locator("text=About the Event").locator("..").locator("..")
    description = None
    if await about.count():
        paras = await about.locator("p").all_text_contents()
        if paras:
            description = "\n".join(p.strip() for p in paras if p.strip())

    event_key = f"district:{event_id}" if event_id else f"district:url:{hash(url)}"
    if event_key in seen:
        return None
    seen.add(event_key)

    # Include all events (past and upcoming) to populate district.json; filter by date elsewhere if needed
    # if not _in_date_range(start_date):
    #     return None

    return _build_event_item(
        event_id=event_id,
        event_name=event_name,
        event_url=url,
        ticket_url=url,
        ticket_price=ticket_price,
        description=description,
        categories=categories,
        start_date=start_date,
        start_time=start_time,
        end_date=None,
        end_time=None,
        venue_name=venue_name,
        venue_address=venue_address,
        organizer_name=None,
    )


def _merge_existing_and_new(
    existing_events: list[dict], new_and_updated: list[dict], urls_scraped_this_run: list[str]
) -> list[dict]:
    """Merge existing events (excluding ones we re-scraped) with new/updated events from this run."""
    urls_scraped_set = set(urls_scraped_this_run)
    kept_existing = [e for e in existing_events if e.get("event_url") not in urls_scraped_set]
    return kept_existing + new_and_updated


def _write_merged(output_path: Path, existing_events: list[dict], new_and_updated: list[dict], urls_scraped: list[str]) -> None:
    """Write merged list to file (for incremental save during run)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged = _merge_existing_and_new(existing_events, new_and_updated, urls_scraped)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


async def run_scraper(output_path: Path, headless: bool = True) -> int:
    """Main scraper logic. Returns count of events scraped. Uses incremental dedup: skips known URLs, re-scrapes stale events."""
    captured_responses: list[dict] = []
    events: list[dict] = []  # New + updated events from this run
    seen: set = set()

    # Load existing district.json for incremental dedup and change detection
    existing_events: list[dict] = []
    existing_by_url: dict[str, dict] = {}
    existing_by_key: dict[str, dict] = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_events = json.load(f)
            if isinstance(existing_events, list):
                for e in existing_events:
                    url = e.get("event_url")
                    key = e.get("event_key")
                    if url:
                        existing_by_url[url] = e
                    if key:
                        existing_by_key[key] = e
            print(f"  Loaded {len(existing_events)} existing events (incremental mode)")
        except Exception as e:
            print(f"  Could not load existing file: {e}")
    known_urls = set(existing_by_url.keys())

    async def handle_response(response):
        url = response.url
        if any(x in url for x in ["get_discovery_results", "gw/web", "mpc", "jumbo", "edition.in/event"]):
            try:
                ct = response.headers.get("content-type") or ""
                if "json" in ct or "application/json" in ct:
                    body = await response.body()
                    data = json.loads(body.decode("utf-8", errors="ignore"))
                    if data:
                        captured_responses.append(data)
            except Exception:
                pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
        )
        context.set_default_timeout(15000)
        page = await context.new_page()
        page.on("response", handle_response)

        # robots.txt: Disallow /*? - no query strings. Use /events/ only.
        print("Opening events page...")
        try:
            await page.goto(EVENTS_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_load_state("load", timeout=PAGE_LOAD_TIMEOUT)
        except PlaywrightTimeout:
            pass
        try:
            await page.wait_for_selector("main, [class*='event'], a[href*='buy-tickets']", timeout=8000)
        except PlaywrightTimeout:
            pass
        await asyncio.sleep(2)

        print("Selecting Bangalore...")
        bangalore_ok = await _select_bangalore(page)
        print(f"  Bangalore selected: {bangalore_ok}")
        await asyncio.sleep(2)

        links = await _collect_event_links_from_listing(page)
        print(f"  Event links from listing: {len(links)}", flush=True)

        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.2)
            more = await _collect_event_links_from_listing(page)
            for u in more:
                if u not in links:
                    links.append(u)
        print(f"  After scroll, total links: {len(links)}")

        # Bangalore category pages as fallback (get Bangalore-only links if modal failed)
        if len(links) < 20:
            for slug in ["music-in-bangalore-book-tickets", "comedy-shows-in-bangalore-book-tickets",
                         "nightlife-in-bangalore-book-tickets", "performances-in-bangalore-book-tickets"]:
                try:
                    await page.goto(f"{EVENTS_URL}{slug}", wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    more = await _collect_event_links_from_listing(page)
                    for u in more:
                        if u not in links:
                            links.append(u)
                except Exception:
                    pass
            print(f"  After Bangalore category fallback, total links: {len(links)}")

        sitemap_links = _fetch_bangalore_urls_from_sitemap()
        print(f"  Sitemap Bangalore URLs: {len(sitemap_links)}")
        # Prefer Bangalore sitemap URLs first; skip category listing pages (e.g. comedy-shows-in-bangalore-book-tickets)
        def is_event_detail(u: str) -> bool:
            return "-in-bangalore-book-tickets" not in u.lower() and "-in-bengaluru-book-tickets" not in u.lower()
        sitemap_event = [u for u in sitemap_links if is_event_detail(u)]
        listing_event = [u for u in links if is_event_detail(u)]
        links = list(dict.fromkeys(sitemap_event + [u for u in listing_event if u not in sitemap_event]))
        print(f"  Event detail URLs to scrape: {len(links)}", flush=True)

        from_api = await _extract_from_api_captures(captured_responses)
        for ev in from_api:
            key = ev.get("event_key")
            if key and key not in seen:
                seen.add(key)
                events.append(ev)
        print(f"  From API captures: {len(from_api)} events")

        # Incremental: only scrape new URLs + stale (older than STALE_DAYS) so we detect changes
        new_urls = [u for u in links if u not in known_urls]
        stale_urls = [u for u in links if u in known_urls and _is_stale(existing_by_url.get(u, {}))]
        to_scrape = list(dict.fromkeys(new_urls + stale_urls))
        skipped = len(links) - len(to_scrape)
        if skipped > 0:
            print(f"  Skipping {skipped} already-known events (re-scrape after {STALE_DAYS} days for updates)")
        if to_scrape:
            print(f"  Scraping {len(to_scrape)} URLs ({len(new_urls)} new, {len(stale_urls)} stale for update check)")
        print(f"  Scraping {len(to_scrape)} event pages...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        for i, url in enumerate(to_scrape, 1):
            if i % 10 == 0 or i == len(to_scrape):
                print(f"    Page {i}/{len(to_scrape)} (events so far: {len(events)})", flush=True)
            ev = await _scrape_event_page(page, url, seen, debug=(i <= 2))
            if ev:
                # Mark if this event was updated (re-scraped) so we can show change
                key = ev.get("event_key")
                if key and key in existing_by_key:
                    ev["updated_in_run"] = True
                    ev["previous_last_updated"] = existing_by_key[key].get("last_updated")
                events.append(ev)
                # Save incrementally so we keep partial results if killed
                _write_merged(output_path, existing_events, events, to_scrape)

        await browser.close()

    # Final merge: keep existing events we didn't re-scrape, add new/updated from this run
    final_events = _merge_existing_and_new(existing_events, events, to_scrape)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_events, f, ensure_ascii=False, indent=2)

    updated_count = sum(1 for e in events if e.get("updated_in_run"))
    if events:
        print(f"  New/updated this run: {len(events)} ({len(events) - updated_count} new, {updated_count} re-scraped for changes)")
    return len(final_events)


def main():
    parser = argparse.ArgumentParser(description="Scrape Bangalore events from Zomato District")
    parser.add_argument("--output", "-o", default="data/district.json", help="Output JSON path")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Show browser")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    output_path = script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)

    print("=" * 60)
    print("Zomato District (district.in) Event Scraper - Bangalore")
    print("=" * 60)
    print(f"Output: {output_path}")
    print("-" * 60)

    n = asyncio.run(run_scraper(output_path, headless=args.headless))
    print(f"\n✓ Scraped {n} Bangalore events")
    print(f"✓ Saved to {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())
