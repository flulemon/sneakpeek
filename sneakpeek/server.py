import asyncio
import logging
from datetime import timedelta
from typing import List

import uvicorn

from sneakpeek.api import create_api
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.base import Storage
from sneakpeek.runner import Runner
from sneakpeek.scheduler import Scheduler
from sneakpeek.scraper import ScraperABC
from sneakpeek.worker import Worker

API_DEFAULT_PORT = 8080
WORKER_DEFAULT_CONCURRENCY = 50
SCHEDULER_DEFAULT_LEASE_DURATION = timedelta(minutes=1)
SCHEDULER_DEFAULT_STORAGE_POLL_DELAY = timedelta(seconds=5)


class SneakpeekServer:
    def __init__(
        self,
        handlers: List[ScraperABC],
        storage: Storage,
        run_api: bool = True,
        run_worker: bool = True,
        run_scheduler: bool = True,
        worker_max_concurrency: int = WORKER_DEFAULT_CONCURRENCY,
        api_port: int = API_DEFAULT_PORT,
        scheduler_storage_poll_delay: timedelta = SCHEDULER_DEFAULT_STORAGE_POLL_DELAY,
        scheduler_lease_duration: timedelta = SCHEDULER_DEFAULT_LEASE_DURATION,
    ) -> None:
        self._storage = storage
        self._queue = Queue(self._storage)
        self._scheduler = Scheduler(
            self._storage,
            self._queue,
            storage_poll_frequency=scheduler_storage_poll_delay,
            lease_duration=scheduler_lease_duration,
        )
        self._runner = Runner(handlers, self._queue, self._storage)
        self._worker = Worker(
            self._runner,
            self._queue,
            max_concurrency=worker_max_concurrency,
        )
        self._api_config = uvicorn.Config(
            create_api(self._storage, self._queue, handlers),
            port=api_port,
        )
        self._api_server = uvicorn.Server(self._api_config)
        self._logger = logging.getLogger(__name__)
        self._run_api = run_api
        self._run_worker = run_worker
        self._run_scheduler = run_scheduler

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._logger.info("Starting sneakpeek server")
        if self._run_scheduler:
            loop.create_task(self._scheduler.start())
        if self._run_worker:
            loop.create_task(self._worker.start())
        if self._run_api:
            loop.create_task(self._api_server.serve())

    async def stop(self) -> None:
        self._logger.info("Stopping sneakpeek server")
        if self._run_scheduler:
            await self._scheduler.stop()
        if self._run_worker:
            await self._worker.stop()
        if self._run_api:
            await self._api_server.shutdown()
