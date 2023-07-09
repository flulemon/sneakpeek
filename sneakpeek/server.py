import asyncio
import logging
from datetime import timedelta
from signal import SIGINT, SIGTERM
from traceback import format_exc

import fastapi_jsonrpc as jsonrpc
import uvicorn

from sneakpeek.api import create_api
from sneakpeek.queue.consumer import Consumer
from sneakpeek.queue.model import QueueStorageABC
from sneakpeek.queue.queue import Queue
from sneakpeek.queue.tasks import (
    DeleteOldTasksHandler,
    KillDeadTasksHandler,
    queue_periodic_tasks,
)
from sneakpeek.scheduler.model import (
    LeaseStorageABC,
    MultiPeriodicTasksStorage,
    SchedulerABC,
)
from sneakpeek.scheduler.scheduler import Scheduler
from sneakpeek.scraper.dynamic_scraper_handler import DynamicScraperHandler
from sneakpeek.scraper.ephemeral_scraper_task_handler import EphemeralScraperTaskHandler
from sneakpeek.scraper.model import Middleware, ScraperHandler, ScraperStorageABC
from sneakpeek.scraper.runner import ScraperRunner
from sneakpeek.scraper.task_handler import ScraperTaskHandler

WEB_SERVER_DEFAULT_PORT = 8080
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
        consumer: Consumer | None = None,
        scheduler: SchedulerABC | None = None,
        web_server: jsonrpc.API | None = None,
        web_server_port: int = WEB_SERVER_DEFAULT_PORT,
    ) -> None:
        """
        Args:
            consumer (Consumer | None, optional): Worker that consumes tasks queue. Defaults to None.
            scheduler (SchedulerABC | None, optional): Scrapers scheduler. Defaults to None.
            web_server (jsonrpc.API | None, optional): Web Server that implements API and exposes UI to interact with the system. Defaults to None.
            web_server_port (int, optional): Port which is used for Web Server (API, UI and metrics). Defaults to 8080.
        """
        self._logger = logging.getLogger(__name__)
        self.consumer = consumer
        self.scheduler = scheduler
        self.api_config = (
            uvicorn.Config(
                web_server, host="0.0.0.0", port=web_server_port, log_config=None
            )
            if web_server
            else None
        )
        self.scheduler = scheduler
        self.web_server = uvicorn.Server(self.api_config) if web_server else None
        self.web_server_task: asyncio.Task | None = None

    @staticmethod
    def create(
        handlers: list[ScraperHandler],
        scraper_storage: ScraperStorageABC,
        queue_storage: QueueStorageABC,
        lease_storage: LeaseStorageABC,
        with_web_server: bool = True,
        with_worker: bool = True,
        with_scheduler: bool = True,
        worker_max_concurrency: int = WORKER_DEFAULT_CONCURRENCY,
        web_server_port: int = WEB_SERVER_DEFAULT_PORT,
        scheduler_storage_poll_delay: timedelta = SCHEDULER_DEFAULT_STORAGE_POLL_DELAY,
        scheduler_lease_duration: timedelta = SCHEDULER_DEFAULT_LEASE_DURATION,
        middlewares: list[Middleware] | None = None,
        add_dynamic_scraper_handler: bool = False,
        session_logger_handler: logging.Handler | None = None,
    ):
        """
        Create Sneakpeek server using default API, worker and scheduler implementations

        Args:
            handlers (list[ScraperHandler]): List of handlers that implement scraper logic
            scraper_storage (ScrapersStorage): Scrapers storage
            jobs_storage (ScraperJobsStorage): Jobs storage
            lease_storage (LeaseStorage): Lease storage
            with_web_server (bool, optional): Whether to run API service. Defaults to True.
            with_worker (bool, optional): Whether to run worker service. Defaults to True.
            with_scheduler (bool, optional): Whether to run scheduler service. Defaults to True.
            worker_max_concurrency (int, optional): Maximum number of concurrently executed scrapers. Defaults to 50.
            web_server_port (int, optional): Port which is used for Web Server (API, UI and metrics). Defaults to 8080.
            scheduler_storage_poll_delay (timedelta, optional): How much scheduler wait before polling storage for scrapers updates. Defaults to 5 seconds.
            scheduler_lease_duration (timedelta, optional): How long scheduler lease lasts. Lease is required for scheduler to be able to create new scraper jobs. This is needed so at any point of time there's only one active scheduler instance. Defaults to 1 minute.
            plugins (list[Plugin] | None, optional): List of plugins that will be used by scraper runner. Can be omitted if run_worker is False. Defaults to None.
            add_dynamic_scraper_handler (bool, optional): Whether to add dynamic scraper handler which can execute arbitrary user scripts. Defaults to False.
        """
        if add_dynamic_scraper_handler:
            dynamic_scraper_handler = DynamicScraperHandler()
            if not any(h for h in handlers if h.name == dynamic_scraper_handler.name):
                handlers.append(dynamic_scraper_handler)

        runner = ScraperRunner(scraper_storage, middlewares)
        queue = Queue(queue_storage)
        task_handlers = [
            KillDeadTasksHandler(queue),
            DeleteOldTasksHandler(queue),
            ScraperTaskHandler(handlers, runner, scraper_storage),
            EphemeralScraperTaskHandler(handlers, runner),
        ]
        periodic_tasks_storage = MultiPeriodicTasksStorage(
            [
                queue_periodic_tasks,
                scraper_storage,
            ]
        )
        scheduler = (
            Scheduler(
                periodic_tasks_storage,
                lease_storage,
                queue,
                tasks_poll_delay=scheduler_storage_poll_delay,
                lease_duration=scheduler_lease_duration,
            )
            if with_scheduler
            else None
        )
        consumer = (
            Consumer(
                queue,
                task_handlers,
                max_concurrency=worker_max_concurrency,
            )
            if with_worker
            else None
        )
        api = (
            create_api(scraper_storage, queue, handlers, session_logger_handler)
            if with_web_server
            else None
        )
        return SneakpeekServer(consumer, scheduler, api, web_server_port)

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
        if self.scheduler:
            self.scheduler.start()
        if self.consumer:
            self.consumer.start()
        if self.web_server:
            self.web_server_task = loop.create_task(self.web_server.serve())
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
        self._logger.info("Stopping sneakpeek server")
        try:
            if self.scheduler:
                self.scheduler.stop()
            if self.consumer:
                self.consumer.stop()
            if self.web_server_task:
                self.web_server_task.cancel()
            loop.stop()
        except Exception:
            self._logger.error(f"Failed to stop: {format_exc()}")
