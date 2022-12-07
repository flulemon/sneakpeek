import logging
from abc import ABC, abstractmethod
from datetime import datetime
from traceback import format_exc
from typing import List

from sneakpeek.lib.errors import UnknownScraperHandlerError
from sneakpeek.lib.models import Scraper, ScraperRun, ScraperRunStatus
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage
from sneakpeek.logging import scraper_run_context
from sneakpeek.scraper_context import Plugin, ScraperContext
from sneakpeek.scraper_handler import ScraperHandler


class RunnerABC(ABC):
    @abstractmethod
    async def run(self, run: ScraperRun) -> None:
        ...


class Runner(RunnerABC):
    def __init__(
        self,
        handlers: List[Scraper],
        queue: QueueABC,
        storage: Storage,
        plugins: list[Plugin] | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._handlers = {handler.name: handler for handler in handlers}
        self._queue = queue
        self._storage = storage
        self._plugins = plugins

    def _get_handler(self, run: ScraperRun) -> ScraperHandler:
        if run.scraper.handler not in self._handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{run.scraper.handler}'"
            )
        return self._handlers[run.scraper.handler]

    async def run(self, run: ScraperRun) -> None:
        with scraper_run_context(run):
            self._logger.info("Starting scraper")
            context = ScraperContext(run.scraper.config, self._plugins)
            try:
                await context.start_session()
                await self._queue.ping_scraper_run(run.scraper.id, run.id)
                handler = self._get_handler(run)
                run.result = await handler.run(context)
                run.status = ScraperRunStatus.SUCCEEDED
            except Exception as e:
                self._logger.error(f"Failed to execute scraper with error: {e}")
                self._logger.debug(f"Traceback: {format_exc()}")
                run.status = ScraperRunStatus.FAILED
                run.result = str(e)
            finally:
                await context.close()
            run.finished_at = datetime.utcnow()
            await self._storage.update_scraper_run(run)
            self._logger.info("Successfully executed scraper")
