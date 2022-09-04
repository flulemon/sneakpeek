import logging
from abc import ABC
from traceback import format_exc

from sneakpeek.lib.models import ScraperRun, ScraperRunStatus
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage


class RunnerABC(ABC):
    async def run(self, run: ScraperRun) -> None:
        raise NotImplementedError()


class Runner(RunnerABC):
    def __init__(self, queue: QueueABC, storage: Storage) -> None:
        self._logger = logging.getLogger(__name__)
        self._queue = queue
        self._storage = storage

    async def run(self, run: ScraperRun) -> None:
        self._logger.info(f"Starting executing {run}")
        try:
            await self._queue.ping_scraper_run(run.scraper.id, run.id)
            run.status = ScraperRunStatus.SUCCEEDED
            run.result = "Successfully finished"
        except Exception as e:
            self._logger.error(f"Failed to execute: {run}: {e}")
            self._logger.debug(f"Failed to execute: {run}. Traceback: {format_exc()}")
            run.status = ScraperRunStatus.FAILED
            run.result = str(e)
        await self._storage.update_scraper_run(run)
        self._logger.info(f"Successfully executed {run}")
