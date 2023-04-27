import logging

from pydantic import BaseModel

from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPlugin
from sneakpeek.runner import LocalRunner
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler


class DemoScraperParams(BaseModel):
    url: str


class DemoScraper(ScraperHandler):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "demo_scraper"

    async def run(self, context: ScraperContext) -> str:
        params = DemoScraperParams.parse_obj(context.params)
        response = await context.get(params.url)
        return (await response.text())[:100]


if __name__ == "__main__":
    LocalRunner.run(
        DemoScraper(),
        ScraperConfig(
            params=DemoScraperParams(
                url="http://google.com",
            ).dict(),
        ),
        plugins=[
            RequestsLoggingPlugin(),
        ],
    )
