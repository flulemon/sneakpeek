import asyncio
import logging

from demo.demo_scraper import DemoScraper, DemoScraperParams
from sneakpeek.config import ScraperConfig
from sneakpeek.lib.models import Scraper, ScraperSchedule
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
from sneakpeek.server import SneakpeekServer

server = SneakpeekServer(
    handlers=[DemoScraper()],
    storage=InMemoryStorage(
        [
            Scraper(
                id=0,
                name="demo_scraper",
                schedule=ScraperSchedule.EVERY_MINUTE,
                handler=DemoScraper().name,
                config=ScraperConfig(
                    scraper_params_json=DemoScraperParams(
                        url="https://google.com",
                    ).json(),
                ),
            )
        ]
    ),
)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    loop.run_forever()
    loop.run_until_complete(server.stop())
