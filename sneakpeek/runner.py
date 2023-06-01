import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from traceback import format_exc
from typing import List

from prometheus_client import Counter

from sneakpeek.errors import (
    ScraperJobPingFinishedError,
    ScraperJobPingNotStartedError,
    ScraperJobTimedOut,
    UnknownScraperHandlerError,
)
from sneakpeek.logging import configure_logging, scraper_job_context
from sneakpeek.metrics import count_invocations, delay_histogram
from sneakpeek.models import Scraper, ScraperJob, ScraperJobStatus
from sneakpeek.queue import QueueABC
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import Plugin, ScraperContext
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.storage.base import ScraperJobsStorage, ScrapersStorage

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
    """Default scraper runner implementation that is meant to be used in the Sneakpeek server"""

    def __init__(
        self,
        handlers: List[ScraperHandler],
        queue: QueueABC,
        scrapers_storage: ScrapersStorage,
        jobs_storage: ScraperJobsStorage,
        plugins: list[Plugin] | None = None,
    ) -> None:
        """
        Args:
            handlers (list[ScraperHandler]): List of handlers that implement scraper logic
            queue (Queue): Sneakpeek queue implementation
            scrapers_storage (ScrapersStorage): Sneakpeek scrapers storage implementation
            jobs_storage (ScraperJobsStorage): Sneakpeek jobs storage implementation
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Defaults to None.
        """
        self._logger = logging.getLogger(__name__)
        self._handlers = {handler.name: handler for handler in handlers}
        self._queue = queue
        self._scrapers_storage = scrapers_storage
        self._jobs_storage = jobs_storage
        self._plugins = plugins

    def _get_handler(self, job: ScraperJob) -> ScraperHandler:
        if job.scraper.handler not in self._handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{job.scraper.handler}'"
            )
        return self._handlers[job.scraper.handler]

    async def _ping_job(self, job: ScraperJob) -> None:
        """Ping scraper job, so it's not considered dead"""
        started = datetime.utcnow()
        deadline = (
            started + timedelta(seconds=job.scraper.timeout_seconds)
            if job.scraper.timeout_seconds
            else datetime.max
        )
        while datetime.utcnow() < deadline:
            try:
                await self._queue.ping_scraper_job(job.scraper.id, job.id)
            except ScraperJobPingNotStartedError as e:
                self._logger.error(
                    f"Failed to ping PENDING scraper job because due to some infra error: {e}"
                )
                raise
            except ScraperJobPingFinishedError as e:
                self._logger.error(
                    f"Failed to ping scraper job because seems like it's been killed: {e}"
                )
                raise
            except Exception as e:
                self._logger.error(f"Failed to ping scraper job: {e}")
            await asyncio.sleep(1)
        raise ScraperJobTimedOut()

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

            async def _update_scraper_state(state: str) -> Scraper:
                scraper = await self._scrapers_storage.get_scraper(job.scraper.id)
                scraper.state = state
                return await self._scrapers_storage.update_scraper(scraper)

            context = ScraperContext(
                job.scraper.config,
                self._plugins,
                scraper_state=job.scraper.state,
                update_scraper_state_func=_update_scraper_state,
            )
            try:
                await context.start_session()
                handler = self._get_handler(job)
                done, _ = await asyncio.wait(
                    [
                        asyncio.create_task(handler.run(context)),
                        asyncio.create_task(self._ping_job(job)),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                coro_result = done.pop()
                job.result = coro_result.result()
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
            await self._jobs_storage.update_scraper_job(job)
            self._logger.info("Successfully executed scraper")


class LocalRunner:
    """Scraper runner that is meant to be used for local debugging"""

    @staticmethod
    async def _update_scraper_state(state: str) -> Scraper | None:
        logging.debug(f"Updating scraper state with: {state}")
        return None

    @staticmethod
    async def run_async(
        handler: ScraperHandler,
        config: ScraperConfig,
        plugins: list[Plugin] | None = None,
        scraper_state: str | None = None,
        logging_level: int = logging.DEBUG,
    ) -> None:
        """
        Execute scraper locally.

        Args:
            handler (ScraperHandler): Scraper handler to execute
            config (ScraperConfig): Scraper config to pass to the handler
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Defaults to None.
            scraper_state (str | None, optional): Scraper state to pass to the handler. Defaults to None.
            logging_level (int, optional): Minimum logging level. Defaults to logging.DEBUG.
        """
        configure_logging(logging_level)
        logging.info("Starting scraper")

        context = ScraperContext(
            config,
            plugins,
            scraper_state=scraper_state,
            update_scraper_state_func=LocalRunner._update_scraper_state,
        )
        try:
            await context.start_session()
            result = await handler.run(context)
            logging.info(f"Scraper succeeded. Result: {result}")
        except Exception as e:
            logging.error(f"Failed to execute scraper with error: {e}")
            logging.error(f"Traceback: {format_exc()}")
        finally:
            await context.close()

    @staticmethod
    def run(
        handler: ScraperHandler,
        config: ScraperConfig,
        plugins: list[Plugin] | None = None,
        scraper_state: str | None = None,
        logging_level: int = logging.DEBUG,
    ) -> None:
        """
        Execute scraper locally.

        Args:
            handler (ScraperHandler): Scraper handler to execute
            config (ScraperConfig): Scraper config to pass to the handler
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Defaults to None.
            scraper_state (str | None, optional): Scraper state to pass to the handler. Defaults to None.
            logging_level (int, optional): Minimum logging level. Defaults to logging.DEBUG.
        """
        asyncio.run(
            LocalRunner.run_async(
                handler,
                config,
                plugins,
                scraper_state,
                logging_level,
            )
        )
