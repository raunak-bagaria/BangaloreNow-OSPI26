import scrapy

# This defines the structure of an event - all the fields we want to collect for each event
class EventItem(scrapy.Item):
    event_id = scrapy.Field()
    event_name = scrapy.Field()
    event_url = scrapy.Field()
    ticket_url = scrapy.Field()
    ticket_price = scrapy.Field()
    description = scrapy.Field()
    categories = scrapy.Field()
    start_date = scrapy.Field()
    start_time = scrapy.Field()
    venue_name = scrapy.Field()
    venue_address = scrapy.Field()
    organizer_name = scrapy.Field()
    city = scrapy.Field()
    source = scrapy.Field()
    source_url = scrapy.Field()
    last_updated = scrapy.Field()
    event_key = scrapy.Field()
