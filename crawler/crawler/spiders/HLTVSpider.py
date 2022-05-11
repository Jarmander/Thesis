import scrapy
from ..items import Demofile


class HLTVSpider(scrapy.Spider):
    name = "hltv"

    def start_requests(self):
        urls = ['https://www.hltv.org/events/archive?startDate=2017-01-01&endDate=2017-12-31&eventType=MAJOR']
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response, **kwargs):
        event_list = response.css('a[href^="/events/"] *::attr(href)').getall()
        for event in event_list:
            if event.rsplit('/')[2].isnumeric():
                metadata = {'event_id': event.rsplit('/')[2],
                            'event_name': event.rsplit('/')[3]}
                url = response.urljoin(event)
                yield scrapy.Request(url=url, callback=self.parse_event, cb_kwargs=dict(metadata=metadata))

    def parse_event(self, response, metadata):
        groups_container = response.css('div[class="groups-container"]')
        group_match_links = groups_container.css('a[href^="/matches/"] *::attr(href)').getall()
        for match in group_match_links:
            metadata['match_id'] = match.rsplit('/')[2]
            url = response.urljoin(match)
            yield scrapy.Request(url=url, callback=self.parse_match, cb_kwargs=dict(metadata=metadata))

    def parse_match(self, response, metadata):
        item = Demofile()
        item['match_id'] = metadata['match_id']
        item['event_id'] = metadata['event_id']
        item['event_name'] = metadata['event_name']
        demo_link = response.css('a[href^="/download/demo/"] *::attr(href)').get()
        demo_link = response.urljoin(demo_link)
        item['file_urls'] = [demo_link]
        yield item

