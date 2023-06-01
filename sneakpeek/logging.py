import logging
from contextlib import contextmanager
from contextvars import ContextVar

from sneakpeek.models import ScraperJob

ctx_scraper_job = ContextVar("scraper_job")


@contextmanager
def scraper_job_context(scraper_job: ScraperJob) -> None:
    """
    Initialize scraper job logging context which automatically adds
    scraper and scraper job IDs to the logging metadata

    Args:
        scraper_job (ScraperJob): Scraper job definition
    """
    try:
        token = ctx_scraper_job.set(scraper_job)
        yield
    finally:
        ctx_scraper_job.reset(token)


class ScraperContextInjectingFilter(logging.Filter):
    """
    Scraper context filter which automatically injects
    scraper and scraper job IDs to the logging metadata.

    Example of usage:

    .. code-block:: python3

        logger = logging.getLogger()
        handler = logging.StreamHandler()
        handler.addFilter(ScraperContextInjectingFilter())
        logger.addHandler(handler)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Injects scraper metadata into log record:

        * ``scraper_job_id`` - Scraper Job ID
        * ``scraper_id`` - Scraper ID
        * ``scraper_name`` - Scraper name
        * ``scraper_handler`` - Scraper logic implementation
        * ``scraper_job_human_name`` - Formatted scraper job ID (``<name>::<scraper_id>::<scraper_job_id>``)

        Args:
            record (logging.LogRecord): Log record to inject metadata into

        Returns:
            bool: Always True
        """
        scraper_job: ScraperJob = ctx_scraper_job.get(None)
        record.scraper_job_human_name = "-"
        if scraper_job:
            record.scraper_job_id = scraper_job.id
            scraper = scraper_job.scraper
            if scraper:
                record.scraper_id = scraper.id
                record.scraper_name = scraper.name
                record.scraper_handler = scraper.handler
                record.scraper_job_human_name = (
                    f"{scraper.name}::{scraper.id}::{scraper_job.id}"
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
            "%(asctime)s][%(levelname)s][%(name)s:%(lineno)d][%(scraper_job_human_name)s] %(message)s"
        )
    )
    handler.addFilter(ScraperContextInjectingFilter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
