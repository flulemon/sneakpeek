import logging
from abc import ABC, abstractmethod
from datetime import datetime
from traceback import format_exc
from typing import List

from prometheus_client import Counter

from sneakpeek.lib.errors import ScraperRunPingFinishedError, UnknownScraperHandlerError
from sneakpeek.lib.models import Scraper, ScraperRun, ScraperRunStatus
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage
from sneakpeek.logging import scraper_run_context
from sneakpeek.metrics import count_invocations, delay_histogram
from sneakpeek.scraper_context import Plugin, ScraperContext
from sneakpeek.scraper_handler import ScraperHandler

scraper_runs = Counter(
    name="scraper_runs",
    documentation="Scraper runs executed",
    namespace="sneakpeek",
    labelnames=["type"],
)


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

    @count_invocations(subsystem="scraper_runner")
    async def run(self, run: ScraperRun) -> None:
        delay_histogram.labels(type="time_spent_in_queue").observe(
            (datetime.utcnow() - run.created_at).total_seconds()
        )
        with scraper_run_context(run):
            self._logger.info("Starting scraper")

            async def ping_session():
                await self._queue.ping_scraper_run(run.scraper.id, run.id)

            context = ScraperContext(run.scraper.config, self._plugins, ping_session)
            try:
                await context.start_session()
                await self._queue.ping_scraper_run(run.scraper.id, run.id)
                handler = self._get_handler(run)
                run.result = await handler.run(context)
                run.status = ScraperRunStatus.SUCCEEDED
                scraper_runs.labels(type="success").inc()
            except ScraperRunPingFinishedError as e:
                self._logger.error(
                    "Scraper run seems to be killed. Not overriding status"
                )
                run.result = str(e)
                scraper_runs.labels(type="killed").inc()
            except Exception as e:
                self._logger.error(f"Failed to execute scraper with error: {e}")
                self._logger.debug(f"Traceback: {format_exc()}")
                run.status = ScraperRunStatus.FAILED
                run.result = str(e)
                scraper_runs.labels(type="failed").inc()
            finally:
                await context.close()
            run.finished_at = datetime.utcnow()
            await self._storage.update_scraper_run(run)
            self._logger.info("Successfully executed scraper")
