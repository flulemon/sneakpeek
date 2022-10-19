import logging

from pydantic import BaseModel

from sneakpeek.context import ScraperContext
from sneakpeek.scraper import ScraperABC


class DemoScraperParams(BaseModel):
    url: str


class DemoScraper(ScraperABC):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "demo_scraper"

    async def run(self, context: ScraperContext) -> str:
        params = DemoScraperParams.parse_raw(context.config.scraper_params_json)
        self._logger.info(f"Starting demo scraper. Will download {params.url}")
        result = await context.get(params.url)
        text = await result.text()
        self._logger.info(f"Downloaded: {text[:250]}")
        return result.text
