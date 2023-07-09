import logging
from contextlib import contextmanager
from contextvars import ContextVar

from sneakpeek.queue.model import Task

ctx_task = ContextVar("scraper_job")


@contextmanager
def task_context(task: Task) -> None:
    """
    Initialize scraper job logging context which automatically adds
    scraper and scraper job IDs to the logging metadata

    Args:
        scraper_job (ScraperJob): Scraper job definition
    """
    try:
        token = ctx_task.set(task)
        yield
    finally:
        ctx_task.reset(token)


class TaskContextInjectingFilter(logging.Filter):
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
        """Injects task metadata into log record:

        * ``task_id`` - Task ID
        * ``task_name`` - Task name
        * ``task_handler`` - Task handler

        Args:
            record (logging.LogRecord): Log record to inject metadata into

        Returns:
            bool: Always True
        """
        task: Task | None = ctx_task.get(None)
        record.task_id = task.id if task else ""
        record.task_name = task.task_name if task else ""
        record.task_handler = task.task_handler if task else ""
        return True


def configure_logging(
    level: int = logging.INFO,
    session_logger_handler: logging.Handler | None = None,
):
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
            "%(asctime)s][%(levelname)s][%(name)s:%(lineno)d]%(task_handler)s:%(task_name)s:%(task_id)s - %(message)s"
        )
    )
    handler.addFilter(TaskContextInjectingFilter())
    logger.addHandler(handler)
    if session_logger_handler:
        logger.addHandler(session_logger_handler)
    logger.setLevel(level)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
