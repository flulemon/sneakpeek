import logging
from abc import ABC
from datetime import datetime
from traceback import format_exc
from typing import List

from sneakpeek.context import ScraperContext
from sneakpeek.lib.errors import UnknownScraperHandlerError
from sneakpeek.lib.models import Scraper, ScraperRun, ScraperRunStatus
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage
from sneakpeek.scraper import ScraperABC


class RunnerABC(ABC):
    async def run(self, run: ScraperRun) -> None:
        raise NotImplementedError()


class Runner(RunnerABC):
    def __init__(
        self,
        handlers: List[Scraper],
        queue: QueueABC,
        storage: Storage,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._handlers = {handler.name: handler for handler in handlers}
        self._queue = queue
        self._storage = storage

    def _get_handler(self, run: ScraperRun) -> ScraperABC:
        if run.scraper.handler not in self._handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{run.scraper.handler}'"
            )
        return self._handlers[run.scraper.handler]

    def _build_context(self, run: ScraperRun) -> ScraperContext:
        return ScraperContext(
            run.scraper.id,
            run.id,
            run.scraper.config,
        )

    async def run(self, run: ScraperRun) -> None:
        human_run_id = f"'{run.scraper.id}::{run.scraper.name}::{run.id}'"
        self._logger.info(f"Running scraper {human_run_id}")
        try:
            await self._queue.ping_scraper_run(run.scraper.id, run.id)
            run.scraper.config
            handler = self._get_handler(run)
            async with self._build_context(run) as context:
                run.result = await handler.run(context)
            run.status = ScraperRunStatus.SUCCEEDED
        except Exception as e:
            self._logger.error(f"Failed to execute: {human_run_id}: {e}")
            self._logger.debug(
                f"Failed to execute: {human_run_id}. Traceback: {format_exc()}"
            )
            run.status = ScraperRunStatus.FAILED
            run.result = str(e)
        run.finished_at = datetime.utcnow()
        await self._storage.update_scraper_run(run)
        self._logger.info(f"Successfully executed {human_run_id}")
