import os
import requests
import scrapy
from scrapy.pipelines.files import FilesPipeline
from urllib.parse import urlparse


class DemofilePipeline(FilesPipeline):

    def file_path(self, request, response=None, info=None, *, item=None):
        match_id = item['match_id']
        event_id = item['event_id']
        event_name = item['event_name']
        return 'files/' + os.path.basename(urlparse(request.url).path)

    def handle_redirect(self, file_url):
        response = requests.head(file_url)
        if response.status_code == 302:
            file_url = response.headers["Location"]
        return file_url

    def get_media_requests(self, item, info):
        redirect_url = self.handle_redirect(item["file_urls"][0])
        yield scrapy.Request(redirect_url)
