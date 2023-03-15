import logging
from abc import ABC, abstractmethod
from datetime import datetime
from traceback import format_exc
from typing import List

from prometheus_client import Counter

from sneakpeek.lib.errors import ScraperJobPingFinishedError, UnknownScraperHandlerError
from sneakpeek.lib.models import Scraper, ScraperJob, ScraperJobStatus
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import ScraperJobsStorage
from sneakpeek.logging import scraper_job_context
from sneakpeek.metrics import count_invocations, delay_histogram
from sneakpeek.scraper_context import Plugin, ScraperContext
from sneakpeek.scraper_handler import ScraperHandler

scraper_jobs = Counter(
    name="scraper_jobs",
    documentation="Scraper jobs executed",
    namespace="sneakpeek",
    labelnames=["type"],
)


class RunnerABC(ABC):
    """Scraper runner - manages scraper job lifecycle and runs the scraper logic"""

    @abstractmethod
    async def run(self, job: ScraperJob) -> None:
        """
        Execute scraper job

        Args:
            job (ScraperJob): Scraper job metadata
        """
        ...


class Runner(RunnerABC):
    """Default scraper jobner implementation"""

    def __init__(
        self,
        handlers: List[Scraper],
        queue: QueueABC,
        storage: ScraperJobsStorage,
        plugins: list[Plugin] | None = None,
    ) -> None:
        """Initialize runner

        Args:
            handlers (list[ScraperHandler]): List of handlers that implement scraper logic
            queue (Queue): Sneakpeek queue implementation
            storage (Storage): Sneakpeek storage implementation
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Defaults to None.
        """
        self._logger = logging.getLogger(__name__)
        self._handlers = {handler.name: handler for handler in handlers}
        self._queue = queue
        self._storage = storage
        self._plugins = plugins

    def _get_handler(self, job: ScraperJob) -> ScraperHandler:
        if job.scraper.handler not in self._handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{job.scraper.handler}'"
            )
        return self._handlers[job.scraper.handler]

    @count_invocations(subsystem="scraper_runner")
    async def run(self, job: ScraperJob) -> None:
        """
        Execute scraper. Following logic is done:

        * Ping scraper job
        * Build scraper context
        * Execute scraper logic
        * [On success] Set scraper job status to ``SUCCEEDED``
        * [On fail] Set scraper job status to ``FAILED``
        * [If the scraper job was killed] Do nothing
        * Persist scraper job status

        Args:
            job (ScraperJob): Scraper job metadata
        """
        delay_histogram.labels(type="time_spent_in_queue").observe(
            (datetime.utcnow() - job.created_at).total_seconds()
        )
        with scraper_job_context(job):
            self._logger.info("Starting scraper")

            async def ping_session():
                await self._queue.ping_scraper_job(job.scraper.id, job.id)

            context = ScraperContext(job.scraper.config, self._plugins, ping_session)
            try:
                await context.start_session()
                await self._queue.ping_scraper_job(job.scraper.id, job.id)
                handler = self._get_handler(job)
                job.result = await handler.run(context)
                job.status = ScraperJobStatus.SUCCEEDED
                scraper_jobs.labels(type="success").inc()
            except ScraperJobPingFinishedError as e:
                self._logger.error(
                    "Scraper run seems to be killed. Not overriding status"
                )
                job.result = str(e)
                scraper_jobs.labels(type="killed").inc()
            except Exception as e:
                self._logger.error(f"Failed to execute scraper with error: {e}")
                self._logger.debug(f"Traceback: {format_exc()}")
                job.status = ScraperJobStatus.FAILED
                job.result = str(e)
                scraper_jobs.labels(type="failed").inc()
            finally:
                await context.close()
            job.finished_at = datetime.utcnow()
            await self._storage.update_scraper_job(job)
            self._logger.info("Successfully executed scraper")
