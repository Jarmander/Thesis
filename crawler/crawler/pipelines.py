from scrapy.pipelines.files import FilesPipeline


class DemofilePipeline(FilesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        match_id = item['match_id']
        event_id = item['event_id']
        event_name = item['event_name']
        return f'files/{event_id}-{event_name}-{match_id}'
