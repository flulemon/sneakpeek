import logging
from abc import ABC
from asyncio import AbstractEventLoop, Lock, get_running_loop, sleep
from datetime import timedelta
from traceback import format_exc
from typing import Dict

from sneakpeek.lib.models import ScraperRun
from sneakpeek.lib.queue import QueueABC
from sneakpeek.runner import RunnerABC


class WorkerABC(ABC):
    async def start(self) -> None:
        raise NotImplementedError()

    async def stop(self) -> None:
        raise NotImplementedError()


class Worker(WorkerABC):
    def __init__(
        self,
        runner: RunnerABC,
        queue: QueueABC,
        loop: AbstractEventLoop | None = None,
        max_concurrency: int = 50,
    ) -> None:
        self._running = False
        self._loop = loop
        self._logger = logging.getLogger(__name__)
        self._lock = Lock()
        self._runner = runner
        self._queue = queue
        self._active: Dict[int, ScraperRun] = {}
        self._max_concurrency = max_concurrency

    async def _execute_scraper(self, scraper_run: ScraperRun) -> None:
        self._logger.info(f"Executing scraper run id={scraper_run.id}")
        try:
            await self._runner.run(scraper_run)
        except Exception as e:
            self._logger.error(f"Failed to execute {scraper_run.id}: {e}")
            self._logger.debug(f"Failed to execute {scraper_run.id}: {format_exc()}")
        del self._active[scraper_run.id]

    async def _on_tick(self) -> None:
        async with self._lock:
            if len(self._active) >= self._max_concurrency:
                self._logger.debug(
                    f"Not dequeuing any tasks because worker has reached max concurrency,"
                    f" there are {len(self._active)} of active tasks"
                )
                return

            dequeued = await self._queue.dequeue()
            if not dequeued:
                self._logger.debug("No pending tasks in the queue")
                return

            self._logger.info(f"Dequeued a job with id={dequeued.id}")
            self._active[dequeued.id] = dequeued
            self._loop.create_task(self._execute_scraper(dequeued))

    async def _worker_loop(self) -> None:
        while self._running:
            await self._on_tick()
            await sleep(timedelta(seconds=1).total_seconds())

    async def start(self) -> None:
        self._logger.info("Starting worker")
        self._running = True
        if not self._loop:
            self._loop = get_running_loop()
        self._loop.create_task(self._worker_loop())

    async def stop(self) -> None:
        self._logger.info(f"Stopping worker. There are {len(self._active)} jobs")
        self._running = False
