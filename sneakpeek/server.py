import asyncio
import logging
from datetime import timedelta
from signal import SIGINT, SIGTERM
from traceback import format_exc

import prometheus_client
import uvicorn

from sneakpeek.api import create_api
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.base import LeaseStorage, ScraperJobsStorage, ScrapersStorage
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
    """
    Sneakpeek server. It can run multiple services at once:

    * API - allows interactions with scrapers storage and scrapers via JsonRPC or UI
    * Worker - executes scheduled scrapers
    * Scheduler - automatically schedules scrapers that are stored in the storage
    """

    def __init__(
        self,
        handlers: list[ScraperHandler],
        scrapers_storage: ScrapersStorage,
        jobs_storage: ScraperJobsStorage,
        lease_storage: LeaseStorage,
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
        """
        Initialize Sneakpeek server

        Args:
            handlers (list[ScraperHandler]): List of handlers that implement scraper logic
            scrapers_storage (ScrapersStorage): Scrapers storage
            jobs_storage (ScraperJobsStorage): Jobs storage
            lease_storage (LeaseStorage): Lease storage
            run_api (bool, optional): Whether to run API service. Defaults to True.
            run_worker (bool, optional): Whether to run worker service. Defaults to True.
            run_scheduler (bool, optional): Whether to run scheduler service. Defaults to True.
            expose_metrics (bool, optional): Whether to expose metrics (prometheus format). Defaults to True.
            worker_max_concurrency (int, optional): Maximum number of concurrently executed scrapers. Defaults to 50.
            api_port (int, optional): Port which is used for API and UI. Defaults to 8080.
            scheduler_storage_poll_delay (timedelta, optional): How much scheduler wait before polling storage for scrapers updates. Defaults to 5 seconds.
            scheduler_lease_duration (timedelta, optional): How long scheduler lease lasts. Lease is required for scheduler to be able to create new scraper runs. This is needed so at any point of time there's only one active scheduler instance. Defaults to 1 minute.
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Can be omitted if run_worker is False. Defaults to None.
            metrics_port (int, optional): Port which is used to expose metric. Defaults to 9090.
        """
        self._scrapers_storage = scrapers_storage
        self._jobs_storage = jobs_storage
        self._lease_storage = lease_storage
        self._queue = Queue(self._scrapers_storage, self._jobs_storage)
        self._scheduler = Scheduler(
            self._scrapers_storage,
            self._jobs_storage,
            self._lease_storage,
            self._queue,
            storage_poll_frequency=scheduler_storage_poll_delay,
            lease_duration=scheduler_lease_duration,
        )
        self._runner = Runner(handlers, self._queue, self._jobs_storage, plugins)
        self._worker = Worker(
            self._runner,
            self._queue,
            max_concurrency=worker_max_concurrency,
        )
        self._api_config = uvicorn.Config(
            create_api(
                self._scrapers_storage,
                self._jobs_storage,
                self._queue,
                handlers,
            ),
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
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        blocking: bool = True,
    ) -> None:
        """
        Start Sneakpeek server

        Args:
            loop (asyncio.AbstractEventLoop | None, optional): AsyncIO loop to use. In case it's None result of `asyncio.get_event_loop()` will be used. Defaults to None.
            blocking (bool, optional): Whether to block thread while server is running. Defaults to True.
        """
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
        """Stop Sneakpeek server

        Args:
            loop (asyncio.AbstractEventLoop | None, optional): AsyncIO loop to use. In case it's None result of `asyncio.get_event_loop()` will be used. Defaults to None.
        """
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
