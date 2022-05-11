import scrapy


class Demofile(scrapy.Item):
    # define the fields for your item here like:
    match_id = scrapy.Field()
    event_id = scrapy.Field()
    event_name = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()

