import random

from demo.demo_scraper import DemoScraper
from sneakpeek.lib.models import Scraper, ScraperRunPriority, ScraperSchedule
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

urls = [
    "https://google.com",
    "https://www.blogger.com",
    "https://youtube.com",
    "https://www.google.com",
    "https://linkedin.com",
    "https://support.google.com",
    "https://play.google.com",
    "https://apple.com",
    "https://microsoft.com",
    "https://cloudflare.com",
    "https://docs.google.com",
    "https://youtu.be",
    "https://wordpress.org",
    "https://en.wikipedia.org",
    "https://whatsapp.com",
    "https://maps.google.com",
    "https://sites.google.com",
    "https://plus.google.com",
    "https://adobe.com",
    "https://drive.google.com",
    "https://europa.eu",
    "https://bp.blogspot.com",
    "https://accounts.google.com",
    "https://googleusercontent.com",
    "https://mozilla.org",
    "https://github.com",
    "https://policies.google.com",
    "https://uol.com.br",
    "https://vk.com",
    "https://istockphoto.com",
    "https://facebook.com",
    "https://vimeo.com",
    "https://amazon.com",
    "https://t.me",
    "https://news.google.com",
    "https://search.google.com",
    "https://enable-javascript.com",
    "https://globo.com",
    "https://www.weebly.com",
    "https://live.com",
    "https://google.de",
    "https://files.wordpress.com",
    "https://paypal.com",
    "https://dailymotion.com",
    "https://google.es",
    "https://bbc.co.uk",
    "https://nih.gov",
    "https://wikimedia.org",
    "https://creativecommons.org",
    "https://who.int",
    "https://feedburner.com",
    "https://brandbucket.com",
    "https://pt.wikipedia.org",
    "https://fr.wikipedia.org",
    "https://theguardian.com",
    "https://ok.ru",
    "https://nytimes.com",
    "https://gstatic.com",
    "https://msn.com",
    "https://opera.com",
    "https://imdb.com",
    "https://tiktok.com",
    "https://developers.google.com",
    "https://slideshare.net",
    "https://jimdofree.com",
    "https://www.yahoo.com",
    "https://draft.blogger.com",
    "https://tools.google.com",
    "https://buydomains.com",
    "https://google.com.br",
    "https://shopify.com",
    "https://google.co.jp",
]

server = SneakpeekServer(
    handlers=[DemoScraper()],
    storage=InMemoryStorage(
        [
            Scraper(
                id=id,
                name=f"Demo Scraper ({url})",
                schedule=ScraperSchedule.EVERY_MINUTE,
                handler=DemoScraper().name,
                config=ScraperConfig(params={"url": url}),
                schedule_priority=random.choice(
                    [
                        ScraperRunPriority.HIGH,
                        ScraperRunPriority.UTMOST,
                        ScraperRunPriority.NORMAL,
                    ]
                ),
            )
            for id, url in enumerate(urls)
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
