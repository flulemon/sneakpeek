from demo.demo_scraper import DemoScraper
from sneakpeek.lib.models import Scraper, ScraperSchedule
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
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

server = SneakpeekServer(
    handlers=[DemoScraper()],
    storage=InMemoryStorage(
        [
            Scraper(
                id=0,
                name="demo_scraper",
                schedule=ScraperSchedule.EVERY_MINUTE,
                handler=DemoScraper().name,
                config=ScraperConfig(params={"url": "https://google.com"}),
            )
        ]
    ),
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
