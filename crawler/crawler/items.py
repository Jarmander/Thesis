# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class Demofile(scrapy.Item):
    # define the fields for your item here like:
    match_id = scrapy.Field()
    event_id = scrapy.Field()
    event_name = scrapy.Field()
    demo_link = scrapy.Field()

