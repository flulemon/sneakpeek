import logging
from contextlib import contextmanager
from contextvars import ContextVar

from sneakpeek.lib.models import ScraperRun

ctx_scraper_run = ContextVar("scraper_run")


@contextmanager
def scraper_run_context(scraper_run: ScraperRun) -> None:
    """
    Initialize scraper run logging context which automatically adds
    scraper and scraper run IDs to the logging metadata

    Args:
        scraper_run (ScraperRun): Scraper run definition
    """
    try:
        token = ctx_scraper_run.set(scraper_run)
        yield
    finally:
        ctx_scraper_run.reset(token)


class ScraperContextInjectingFilter(logging.Filter):
    """
    Scraper context filter which automatically injects
    scraper and scraper run IDs to the logging metadata.

    Example of usage:

    .. code-block:: python3

        logger = logging.getLogger()
        handler = logging.StreamHandler()
        handler.addFilter(ScraperContextInjectingFilter())
        logger.addHandler(handler)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Injects scraper metadata into log record:

        * ``scraper_run_id`` - Scraper Run ID
        * ``scraper_id`` - Scraper ID
        * ``scraper_name`` - Scraper name
        * ``scraper_handler`` - Scraper logic implementation
        * ``scraper_run_human_name`` - Formatted scraper run ID (``<name>::<scraper_id>::<scraper_run_id>``)

        Args:
            record (logging.LogRecord): Log record to inject metadata into

        Returns:
            bool: Always True
        """
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
    """
    Helper function to configure logging:

    * Adds console logger to the root logger
    * Adds scraper context injector filter to the console logger
    * Configures console formatting to use scraper metadata

    Args:
        level (int, optional): Minimum logging level. Defaults to logging.INFO.
    """
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
