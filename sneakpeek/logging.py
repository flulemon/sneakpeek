import logging
from contextlib import contextmanager
from contextvars import ContextVar

from sneakpeek.lib.models import ScraperRun

ctx_scraper_run = ContextVar("scraper_run")


@contextmanager
def scraper_run_context(scraper_run: ScraperRun) -> None:
    try:
        token = ctx_scraper_run.set(scraper_run)
        yield
    finally:
        ctx_scraper_run.reset(token)


class ScraperContextInjectingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        scraper_run: ScraperRun = ctx_scraper_run.get(None)
        record.scraper_run_human_name = "-"
        if scraper_run:
            record.scraper_run_id = scraper_run.id
            scraper = scraper_run.scraper
            if scraper:
                record.scraper_id = scraper.id
                record.scraper_name = scraper.name
                record.scraper_handler = scraper.handler
                record.scraper_run_human_name = (
                    f"{scraper.name}::{scraper.id}::{scraper_run.id}"
                )
        return True


def configure_logging(level: int = logging.INFO):
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s][%(levelname)s][%(name)s:%(lineno)d][%(scraper_run_human_name)s] %(message)s"
        )
    )
    handler.addFilter(ScraperContextInjectingFilter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
