import random

from demo_scraper import DemoScraper

from sneakpeek.lib.models import Scraper, ScraperJobPriority, ScraperSchedule
from sneakpeek.lib.storage.in_memory_storage import (
    InMemoryLeaseStorage,
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.logging import configure_logging
from sneakpeek.plugins.rate_limiter_plugin import (
    RateLimiterPlugin,
    RateLimiterPluginConfig,
)
from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPlugin
from sneakpeek.plugins.robots_txt_plugin import RobotsTxtPlugin
from sneakpeek.plugins.user_agent_injecter_plugin import (
    UserAgentInjecterPlugin,
    UserAgentInjecterPluginConfig,
)
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.server import SneakpeekServer

urls = [
    "https://google.com",
    "https://www.blogger.com",
    "https://youtube.com",
    "https://www.google.com",
    "https://linkedin.com",
]

scrapers = [
    Scraper(
        id=id,
        name=f"Demo Scraper ({url})",
        schedule=ScraperSchedule.EVERY_MINUTE,
        handler=DemoScraper().name,
        config=ScraperConfig(params={"url": url}),
        schedule_priority=random.choice(
            [
                ScraperJobPriority.HIGH,
                ScraperJobPriority.UTMOST,
                ScraperJobPriority.NORMAL,
            ]
        ),
    )
    for id, url in enumerate(urls)
]

scrapers_storage = InMemoryScrapersStorage(scrapers)
jobs_storage = InMemoryScraperJobsStorage()
lease_storage = InMemoryLeaseStorage()

server = SneakpeekServer(
    handlers=[DemoScraper()],
    scrapers_storage=scrapers_storage,
    jobs_storage=jobs_storage,
    lease_storage=lease_storage,
    plugins=[
        RequestsLoggingPlugin(),
        RobotsTxtPlugin(),
        RateLimiterPlugin(RateLimiterPluginConfig(max_rpm=60)),
        UserAgentInjecterPlugin(UserAgentInjecterPluginConfig(use_external_data=False)),
    ],
)

if __name__ == "__main__":
    configure_logging()
    server.serve()
