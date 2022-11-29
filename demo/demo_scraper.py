import logging

from pydantic import BaseModel

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
        self._logger.info(f"Starting demo scraper. Will download {params.url}")
        result = await context.get(params.url)
        text = await result.text()
        self._logger.info(f"Downloaded: {text[:250]}")
        return result.text()
