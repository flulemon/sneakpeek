import asyncio

from demo.demo_scraper import DemoScraper
from sneakpeek.lib.models import Scraper, ScraperSchedule
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
from sneakpeek.logging import configure_logging
from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPlugin
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.server import SneakpeekServer

server = SneakpeekServer(
    handlers=[DemoScraper()],
    storage=InMemoryStorage(
        [
            Scraper(
                id=0,
                name="demo_scraper",
                schedule=ScraperSchedule.EVERY_SECOND,
                handler=DemoScraper().name,
                config=ScraperConfig(params={"url": "https://google.com"}),
            )
        ]
    ),
    plugins=[RequestsLoggingPlugin()],
)

if __name__ == "__main__":
    configure_logging()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    loop.run_forever()
    loop.run_until_complete(server.stop())
