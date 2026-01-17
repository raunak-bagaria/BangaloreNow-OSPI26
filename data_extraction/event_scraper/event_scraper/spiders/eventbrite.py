import scrapy
from scrapy_playwright.page import PageMethod
import re
import json
from event_scraper.items import EventItem
from datetime import datetime, timedelta
from urllib.parse import urlencode


class EventbriteSpider(scrapy.Spider):
    name = "eventbrite"
    allowed_domains = ["eventbrite.com"]
    
    MAX_DAYS_AHEAD = 90
    
    custom_settings = {
        "CLOSESPIDER_PAGECOUNT": 100,
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 2,
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
        },
    }
    
    def start_requests(self):
        """
        Generate initial requests for Bangalore events on Eventbrite
        """
        # Calculate date range
        today = datetime.now().date()
        cutoff_date = today + timedelta(days=self.MAX_DAYS_AHEAD)
        
        # Eventbrite uses a location-based URL structure
        # Format: https://www.eventbrite.com/d/india--bangalore/events/
        base_url = "https://www.eventbrite.com/d/india--bangalore/events/"
        
        yield scrapy.Request(
            url=base_url,
            callback=self.parse,
            meta={
                "page": 1,
                "today": today,
                "cutoff_date": cutoff_date,
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "a[href*='/e/']", timeout=10000),
                ],
            }
        )
    
    def parse(self, response):
        """
        Parse the event listing page and extract event links
        """
        today = response.meta["today"]
        cutoff_date = response.meta["cutoff_date"]
        page = response.meta.get("page", 1)
        
        self.logger.info(f"Parsing page {page}")
        
        # Eventbrite uses JSON-LD structured data and also renders events in the page
        # Try to extract from structured data first
        json_ld_scripts = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        
        event_urls = set()
        
        # Method 1: Extract from JSON-LD
        for script in json_ld_scripts:
            try:
                data = json.loads(script)
                if isinstance(data, dict):
                    if data.get("@type") == "Event":
                        url = data.get("url")
                        if url:
                            event_urls.add(url)
                    elif data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                        for item in items:
                            if isinstance(item, dict):
                                url = item.get("url")
                                if url:
                                    event_urls.add(url)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            url = item.get("url")
                            if url:
                                event_urls.add(url)
            except json.JSONDecodeError:
                continue
        
        # Method 2: Extract from event cards/links in HTML
        # Look for links that match Eventbrite event URL pattern
        event_links = response.css('a[href*="/e/"]::attr(href)').getall()
        for link in event_links:
            # Eventbrite event URLs typically have format: /e/event-name-tickets-123456789
            if '/e/' in link and 'tickets' in link:
                full_url = response.urljoin(link)
                event_urls.add(full_url)
        
        # Alternative selectors for event cards
        card_links = response.css('article a::attr(href), .event-card a::attr(href), [data-testid*="event"] a::attr(href)').getall()
        for link in card_links:
            if link and '/e/' in link:
                full_url = response.urljoin(link)
                event_urls.add(full_url)
        
        self.logger.info(f"Found {len(event_urls)} event URLs on page {page}")
        
        # Request each event page
        for url in event_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_event,
                meta={
                    "today": today,
                    "cutoff_date": cutoff_date,
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                }
            )
        
        # Handle pagination
        # Eventbrite uses ?page=N URL parameter
        if page < 20:  # Limit to 20 pages max to get more events
            next_page_num = page + 1
            next_url = f"https://www.eventbrite.com/d/india--bangalore/events/?page={next_page_num}"
            self.logger.info(f"Following pagination to page {next_page_num}: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={
                    "page": next_page_num,
                    "today": today,
                    "cutoff_date": cutoff_date,
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "a[href*='/e/']", timeout=10000),
                    ],
                }
            )
    
    def parse_event(self, response):
        """
        Parse individual event page
        """
        today = response.meta.get("today")
        cutoff_date = response.meta.get("cutoff_date")
        
        # Extract structured data from JSON-LD
        json_ld = response.xpath('//script[@type="application/ld+json"]/text()').get()
        
        event_schema = {}
        if json_ld:
            try:
                data = json.loads(json_ld)
                if isinstance(data, list):
                    for block in data:
                        if block.get("@type") == "Event":
                            event_schema = block
                            break
                elif data.get("@type") == "Event":
                    event_schema = data
            except json.JSONDecodeError:
                pass
        
        # Extract event ID from URL
        # URL format: https://www.eventbrite.com/e/event-name-tickets-123456789
        event_id = None
        id_match = re.search(r'/e/[^/]+-(\d+)', response.url)
        if id_match:
            event_id = id_match.group(1)
        
        if not event_id:
            # Try alternative extraction from page
            event_id = response.css('[data-event-id]::attr(data-event-id)').get()
        
        # Create unique event key
        if event_id:
            event_key = f"eventbrite:{event_id}"
        else:
            event_key = f"eventbrite:url:{hash(response.url)}"
        
        # Extract event name
        event_name = None
        if event_schema:
            event_name = event_schema.get("name")
        if not event_name:
            event_name = response.css('h1::text, .event-title::text').get()
        if not event_name:
            event_name = response.xpath('//meta[@property="og:title"]/@content').get()
        
        # Extract description
        description = None
        if event_schema:
            description = event_schema.get("description")
        if not description:
            # Try to get from meta tags
            description = response.xpath('//meta[@property="og:description"]/@content').get()
        if not description:
            # Try to get from page content
            desc_parts = response.css('.event-description::text, .description::text').getall()
            description = " ".join([d.strip() for d in desc_parts if d.strip()])
        
        # Extract dates and times - PRIMARY: from meta tags (most reliable)
        start_date = None
        start_time = None
        end_date = None
        end_time = None
        
        # Method 1: Extract from Open Graph meta tags (most reliable for Eventbrite)
        start_time_meta = response.xpath('//meta[@property="event:start_time"]/@content').get()
        end_time_meta = response.xpath('//meta[@property="event:end_time"]/@content').get()
        
        if start_time_meta:
            try:
                # Format: 2026-01-22T17:30:00+05:30
                if "T" in start_time_meta:
                    date_part, time_part = start_time_meta.split("T")
                    start_date = date_part
                    # Extract time without timezone
                    start_time = time_part.split("+")[0].split("-")[0][:5]  # Get HH:MM
            except Exception as e:
                self.logger.debug(f"Error parsing start_time_meta: {e}")
        
        if end_time_meta:
            try:
                # Format: 2026-01-22T20:30:00+05:30
                if "T" in end_time_meta:
                    date_part, time_part = end_time_meta.split("T")
                    end_date = date_part
                    # Extract time without timezone
                    end_time = time_part.split("+")[0].split("-")[0][:5]  # Get HH:MM
            except Exception as e:
                self.logger.debug(f"Error parsing end_time_meta: {e}")
        
        # Method 2: Fallback to JSON-LD if meta tags not found
        if not start_date and event_schema:
            start_dt = event_schema.get("startDate")
            if start_dt:
                try:
                    if "T" in start_dt:
                        date_part, time_part = start_dt.split("T", 1)
                        start_date = date_part
                        start_time = time_part.split("+")[0].split("-")[0][:5]
                    else:
                        start_date = start_dt
                except Exception:
                    pass
            
            end_dt = event_schema.get("endDate")
            if end_dt:
                try:
                    if "T" in end_dt:
                        date_part, time_part = end_dt.split("T", 1)
                        end_date = date_part
                        end_time = time_part.split("+")[0].split("-")[0][:5]
                    else:
                        end_date = end_dt
                except Exception:
                    pass
        
        # Check if event is within date range
        if start_date and cutoff_date:
            try:
                event_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                if event_date > cutoff_date:
                    self.logger.info(f"Skipping event {event_id}: date {start_date} is beyond cutoff {cutoff_date}")
                    return
            except Exception:
                pass
        
        # Extract venue information
        venue_name = None
        venue_address = None
        
        if event_schema:
            location = event_schema.get("location", {})
            if isinstance(location, dict):
                venue_name = location.get("name")
                address = location.get("address", {})
                if isinstance(address, dict):
                    address_parts = [
                        address.get("streetAddress"),
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("postalCode"),
                        address.get("addressCountry")
                    ]
                    venue_address = ", ".join(filter(None, address_parts))
        
        # Fallback: extract venue from page with multiple selectors
        if not venue_name:
            venue_selectors = [
                '[data-testid*="venue"]::text',
                '[data-testid*="location"]::text',
                '.venue-name::text',
                '.location-name::text',
                '[class*="venue"]::text',
                '[class*="Venue"]::text',
                'div:contains("Location") + div::text',
                'span:contains("Where")::text',
            ]
            
            for selector in venue_selectors:
                venue_name = response.css(selector).get()
                if venue_name:
                    venue_name = venue_name.strip()
                    if len(venue_name) > 3:  # Avoid single characters
                        break
        
        if not venue_address:
            address_selectors = [
                '.venue-address::text',
                '.location-address::text',
                '[data-testid*="address"]::text',
                '[class*="address"]::text',
            ]
            
            for selector in address_selectors:
                address_parts = response.css(selector).getall()
                if address_parts:
                    venue_address = ", ".join([a.strip() for a in address_parts if a.strip()])
                    if venue_address:
                        break
        
        # Extract organizer
        organizer_name = None
        if event_schema:
            organizer = event_schema.get("organizer")
            if isinstance(organizer, dict):
                organizer_name = organizer.get("name")
        
        if not organizer_name:
            organizer_selectors = [
                '[data-testid*="organizer"]::text',
                '.organizer-name::text',
                '[class*="organizer"]::text',
                'a[href*="/o/"]::text',
                'div:contains("Organizer") + div::text',
                'div:contains("Hosted by")::text',
                'div:contains("By")::text',
            ]
            
            for selector in organizer_selectors:
                organizer_name = response.css(selector).get()
                if organizer_name:
                    organizer_name = organizer_name.strip()
                    # Clean up common prefixes
                    organizer_name = re.sub(r'^(By |Hosted by |Organizer: |Organized by )', '', organizer_name, flags=re.IGNORECASE)
                    if len(organizer_name) > 2:
                        break
        
        # Extract category
        categories = None
        if event_schema:
            category = event_schema.get("category")
            if category:
                categories = category if isinstance(category, str) else str(category)
        
        if not categories:
            cat_selectors = [
                '[data-testid*="category"]::text',
                '.event-category::text',
                '.category::text',
                '[class*="Category"]::text',
                'meta[property="article:tag"]::attr(content)',
            ]
            
            cat_list = []
            for selector in cat_selectors:
                cat_elements = response.css(selector).getall()
                for cat in cat_elements:
                    if cat:
                        cat = cat.strip()
                        if cat and len(cat) > 2 and cat not in cat_list:
                            cat_list.append(cat)
            
            if cat_list:
                categories = ", ".join(cat_list)
        
        # Extract ticket info
        ticket_price = "Paid"  # Default assumption
        ticket_url = response.url
        
        # Check for free events with multiple selectors
        free_selectors = [
            '[data-testid*="price"]::text',
            '.price::text',
            '.ticket-price::text',
            '[class*="Price"]::text',
            'button:contains("Free")::text',
            'span:contains("Free")::text',
            'div:contains("Free")::text',
        ]
        
        for selector in free_selectors:
            free_indicators = response.css(selector).getall()
            for indicator in free_indicators:
                if indicator and "free" in indicator.lower():
                    ticket_price = "Free"
                    break
            if ticket_price == "Free":
                break
        
        if event_schema and ticket_price != "Free":
            offers = event_schema.get("offers", {})
            if isinstance(offers, dict):
                price = offers.get("price")
                if price == "0" or price == 0 or price == "0.00":
                    ticket_price = "Free"
            elif isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        price = offer.get("price")
                        if price == "0" or price == 0 or price == "0.00":
                            ticket_price = "Free"
                            break
        
        # Create EventItem
        item = EventItem()
        item["event_id"] = event_id
        item["event_name"] = event_name
        item["event_url"] = response.url
        item["ticket_url"] = ticket_url
        item["ticket_price"] = ticket_price
        item["description"] = description
        item["categories"] = categories
        item["start_date"] = start_date
        item["start_time"] = start_time
        item["end_date"] = end_date
        item["end_time"] = end_time
        item["venue_name"] = venue_name
        item["venue_address"] = venue_address
        item["organizer_name"] = organizer_name
        item["city"] = "Bangalore"
        item["source"] = "eventbrite"
        item["source_url"] = response.url
        item["last_updated"] = datetime.now().isoformat()
        item["event_key"] = event_key
        
        yield item
