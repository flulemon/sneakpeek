import asyncio
import logging
from datetime import timedelta
from signal import SIGINT, SIGTERM
from traceback import format_exc

import prometheus_client
import uvicorn

from sneakpeek.api import create_api
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.base import Storage
from sneakpeek.runner import Runner
from sneakpeek.scheduler import Scheduler
from sneakpeek.scraper_context import Plugin
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.worker import Worker

API_DEFAULT_PORT = 8080
METRICS_DEFAULT_PORT = 9090
WORKER_DEFAULT_CONCURRENCY = 50
SCHEDULER_DEFAULT_LEASE_DURATION = timedelta(minutes=1)
SCHEDULER_DEFAULT_STORAGE_POLL_DELAY = timedelta(seconds=5)


class SneakpeekServer:
    def __init__(
        self,
        handlers: list[ScraperHandler],
        storage: Storage,
        run_api: bool = True,
        run_worker: bool = True,
        run_scheduler: bool = True,
        expose_metrics: bool = True,
        worker_max_concurrency: int = WORKER_DEFAULT_CONCURRENCY,
        api_port: int = API_DEFAULT_PORT,
        scheduler_storage_poll_delay: timedelta = SCHEDULER_DEFAULT_STORAGE_POLL_DELAY,
        scheduler_lease_duration: timedelta = SCHEDULER_DEFAULT_LEASE_DURATION,
        plugins: list[Plugin] | None = None,
        metrics_port: int = METRICS_DEFAULT_PORT,
    ) -> None:
        self._storage = storage
        self._queue = Queue(self._storage)
        self._scheduler = Scheduler(
            self._storage,
            self._queue,
            storage_poll_frequency=scheduler_storage_poll_delay,
            lease_duration=scheduler_lease_duration,
        )
        self._runner = Runner(handlers, self._queue, self._storage, plugins)
        self._worker = Worker(
            self._runner,
            self._queue,
            max_concurrency=worker_max_concurrency,
        )
        self._api_config = uvicorn.Config(
            create_api(self._storage, self._queue, handlers),
            host="0.0.0.0",
            port=api_port,
            log_config=None,
        )
        self._api_server = uvicorn.Server(self._api_config)
        self._logger = logging.getLogger(__name__)
        self._run_api = run_api
        self._run_worker = run_worker
        self._run_scheduler = run_scheduler
        self._expose_metrics = expose_metrics
        self._metrics_port = metrics_port

    def serve(
        self, loop: asyncio.AbstractEventLoop | None = None, blocking: bool = True
    ) -> None:
        loop = loop or asyncio.get_event_loop()
        self._logger.info("Starting sneakpeek server")
        if self._run_scheduler:
            loop.create_task(self._scheduler.start())
        if self._run_worker:
            loop.create_task(self._worker.start())
        if self._run_api:
            loop.create_task(self._api_server.serve())
        if self._expose_metrics:
            prometheus_client.start_http_server(self._metrics_port)
        loop.create_task(self._install_signals())
        if blocking:
            loop.run_forever()

    async def _install_signals(self) -> None:
        loop = asyncio.get_running_loop()
        for signal in [SIGINT, SIGTERM]:
            loop.add_signal_handler(signal, self.stop, loop)

    def stop(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        loop = loop or asyncio.get_event_loop()
        loop.stop()
        self._logger.info("Stopping sneakpeek server")
        try:
            if self._run_scheduler:
                self._scheduler.stop()
            if self._run_worker:
                self._worker.stop()
        except Exception:
            self._logger.error(f"Failed to stop: {format_exc()}")
