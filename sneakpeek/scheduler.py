import asyncio
import logging
from abc import ABC, abstractmethod
from asyncio import Lock
from datetime import datetime, timedelta
from traceback import format_exc
from typing import Dict
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from prometheus_client import Gauge

from sneakpeek.errors import ScraperHasActiveRunError
from sneakpeek.metrics import count_invocations, measure_latency, replicas_gauge
from sneakpeek.models import Lease, Scraper, ScraperJobPriority, ScraperSchedule
from sneakpeek.queue import QueueABC
from sneakpeek.storage.base import LeaseStorage, ScraperJobsStorage, ScrapersStorage

DEFAULT_LEASE_DURATION = timedelta(minutes=1)
DEFAULT_STORAGE_POLL_DELAY = timedelta(seconds=5)
DEFAULT_RUNS_TO_KEEP = 100


queue_length_gauge = Gauge(
    name="queue_length",
    documentation="Number of pending scraper jobs",
    namespace="sneakpeek",
    labelnames=["priority"],
)


class SchedulerABC(ABC):
    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...


class Scheduler(SchedulerABC):
    """Sneakpeeker scheduler - schedules scrapers and performs maintenance jobs. Uses APScheduler under the hood."""

    def __init__(
        self,
        scrapers_storage: ScrapersStorage,
        jobs_storage: ScraperJobsStorage,
        lease_storage: LeaseStorage,
        queue: QueueABC,
        storage_poll_frequency: timedelta = DEFAULT_STORAGE_POLL_DELAY,
        lease_duration: timedelta = DEFAULT_LEASE_DURATION,
        jobs_to_keep: int = 100,
    ) -> None:
        """Initialize scheduler

        Args:
            scrapers_storage (ScrapersStorage): Scrapers storage
            jobs_storage (ScraperJobsStorage): Jobs storage
            lease_storage (LeaseStorage): Lease storage
            queue (Queue): Sneakpeek queue implementation
            storage_poll_frequency (timedelta, optional): How much scheduler wait before polling storage for scrapers updates. Defaults to 5 seconds.
            lease_duration (timedelta, optional): How long scheduler lease lasts. Lease is required for scheduler to be able to create new scraper jobs. This is needed so at any point of time there's only one active scheduler instance. Defaults to 1 minute.
            jobs_to_keep (int, optional): Maximum number of historical scraper jobs to keep in the storage. Storage is cleaned up every 10 minutes. Defaults to 100.
        """
        self._lease_name = "sneakpeek:scheduler"
        self._owner_id = str(uuid4())
        self._lease_duration = lease_duration
        self._scrapers_storage = scrapers_storage
        self._jobs_storage = jobs_storage
        self._lease_storage = lease_storage
        self._queue = queue
        self._scheduler = AsyncIOScheduler()
        self._lease: Lease | None = None
        self._lock = Lock()
        self._scrapers: Dict[int, Scraper] = {}
        self._logger = logging.getLogger(__name__)
        self._scheduler.add_job(
            self._on_tick,
            trigger="interval",
            seconds=int(storage_poll_frequency.total_seconds()),
            id="scheduler:internal:on_tick",
            max_instances=1,
        )
        self._max_kill_dead_jobs_concurrency = 10
        self._scheduler.add_job(
            self._kill_dead_scraper_jobs,
            trigger="interval",
            seconds=int(timedelta(minutes=1).total_seconds()),
            id="scheduler:internal:kill_dead_jobs",
            max_instances=1,
        )
        self._scheduler.add_job(
            self._export_queue_len,
            trigger="interval",
            seconds=int(timedelta(seconds=5).total_seconds()),
            id="scheduler:internal:export_queue_len",
            max_instances=1,
        )
        self._jobs_to_keep = jobs_to_keep
        self._scheduler.add_job(
            self._delete_old_scraper_jobs,
            trigger="interval",
            seconds=int(timedelta(minutes=10).total_seconds()),
            id="scheduler:internal:delete_old_jobs",
            max_instances=1,
        )

    @property
    def _is_lease_acquired(self) -> bool:
        return (
            self._lease
            and self._lease.acquired
            and datetime.utcnow() < self._lease.acquired_until
        )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _enqueue_scraper(self, scraper_id: int) -> None:
        if not self._is_lease_acquired:
            self._logger.debug(
                f"Couldn't enqueue scraper id={scraper_id} because lease is not acquired"
            )
            return
        scraper = self._scrapers.get(scraper_id)
        if not scraper:
            self._logger.warning(f"Tried to enqueue unknown scraper: {scraper_id}")
            return

        scraper_human_id = f"'{scraper.name}'::{scraper.id}"
        self._logger.debug(f"Trying to enqueue scraper {scraper_human_id}")
        try:
            scraper_job = await self._queue.enqueue(
                scraper.id,
                scraper.schedule_priority,
            )
            self._logger.info(
                f"Successfully enqueued scraper {scraper_human_id}::{scraper_job.id}"
            )
        except ScraperHasActiveRunError as e:
            self._logger.debug(f"Failed to enqueue {scraper_human_id}: {e}")
        except Exception as e:
            self._logger.error(f"Failed to enqueue {scraper_human_id}: {e}")
            self._logger.debug(
                f"Failed to enqueue {scraper_human_id}. Traceback: {format_exc()}"
            )

    async def _get_scraper_trigger(self, scraper: Scraper) -> BaseTrigger | None:
        start_date = datetime.min
        scraper_jobs = await self._jobs_storage.get_scraper_jobs(scraper.id)
        if scraper_jobs:
            last_run = sorted(scraper_jobs, key=lambda x: x.id, reverse=True)[0]
            start_date = last_run.finished_at
        match scraper.schedule:
            case ScraperSchedule.CRONTAB:
                return CronTrigger.from_crontab(scraper.schedule_crontab)
            case ScraperSchedule.EVERY_HOUR:
                return IntervalTrigger(hours=1, start_date=start_date)
            case ScraperSchedule.EVERY_DAY:
                return IntervalTrigger(days=1, start_date=start_date)
            case ScraperSchedule.EVERY_WEEK:
                return IntervalTrigger(weeks=1, start_date=start_date)
            case ScraperSchedule.EVERY_MONTH:
                return IntervalTrigger(days=30, start_date=start_date)
            case ScraperSchedule.EVERY_MINUTE:
                return IntervalTrigger(minutes=1, start_date=start_date)
            case ScraperSchedule.EVERY_SECOND:
                return IntervalTrigger(seconds=1, start_date=start_date)
            case ScraperSchedule.INACTIVE:
                return None
            case _:
                raise ValueError(f"Unsupported Scraper schedule: {scraper.schedule}")

    def _remove_scraper_job(self, scraper) -> None:
        logging.info(f"Removing scraper enqueue job: {scraper}")
        self._scheduler.remove_job(f"scheduler:scraper:{scraper.id}")
        del self._scrapers[scraper.id]

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _update_scraper_job(
        self,
        scraper: Scraper,
        remove_existing: bool,
    ) -> None:
        """Add or update internal scheduler job for the scraper.

        Args:
            scraper (Scraper): Scraper metadata
            remove_existing (bool): If True will remove internal scheduler job before adding a new one.
        """
        logging.info(
            f"{'Updating' if remove_existing else 'Adding'} scraper enqueue job: '{scraper.name}'::{scraper.id}"
        )
        job_id = f"scheduler:scraper:{scraper.id}"
        trigger = await self._get_scraper_trigger(scraper)
        self._scrapers[scraper.id] = scraper
        if remove_existing:
            self._scheduler.remove_job(job_id)
        if trigger:
            self._scheduler.add_job(
                self._enqueue_scraper,
                trigger,
                id=job_id,
                args=(scraper.id,),
            )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _update_scrapers_jobs(self) -> None:
        """Poll storage for all existing scrapers and update corresponding scheduler jobs"""
        scrapers = await self._scrapers_storage.get_scrapers()
        index = {scraper.id: scraper for scraper in scrapers}
        for existing in self._scrapers.values():
            if (
                existing.id not in index
                or existing.schedule == ScraperSchedule.INACTIVE
            ):
                self._remove_scraper_job(existing)
            elif self._scrapers[existing.id] != index[existing.id]:
                await self._update_scraper_job(index[existing.id], remove_existing=True)

        for scraper in index.values():
            if scraper.id not in self._scrapers:
                await self._update_scraper_job(scraper, remove_existing=False)

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _on_tick(self) -> None:
        """Periodic job that:

        * Tries to acquire lease to ensure that there's only single active scheduler replica that can enqueue jobs
        * Updates internal (APScheduler) jobs that enqueue scrapers
        """
        replicas_gauge.labels(type="total_scheduler").set(1)
        try:
            self._logger.debug("Starting scheduler update cycle")
            self._logger.debug("Trying to acquire lease")
            self._lease = await self._lease_storage.maybe_acquire_lease(
                self._lease_name,
                self._owner_id,
                self._lease_duration,
            )
            if self._lease:
                replicas_gauge.labels(type="active_scheduler").set(1)
                self._logger.info(
                    f"Successfully acquired lease until {self._lease.acquired_until.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                replicas_gauge.labels(type="active_scheduler").set(0)
            await self._update_scrapers_jobs()
        except Exception as e:
            self._logger.error(f"Scheduler on tick function failed: {e}")
            self._logger.debug(
                f"Scheduler on tick function failed. Traceback: {format_exc()}"
            )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _kill_dead_scraper_jobs(self) -> None:
        """Periodic job that kills scraper jobs that are active but haven't been pinged for a while"""
        if not self._is_lease_acquired:
            return
        try:
            semaphore = asyncio.Semaphore(self._max_kill_dead_jobs_concurrency)

            async def kill_dead_jobs(scraper_id):
                async with semaphore:
                    return await self._queue.kill_dead_scraper_jobs(scraper_id)

            scrapers = list(self._scrapers.keys())
            self._logger.info(f"Killing dead jobs for {len(scrapers)} scrapers")
            kill_jobs = [kill_dead_jobs(scraper) for scraper in scrapers]
            results = await asyncio.gather(*kill_jobs, return_exceptions=True)
            killed = sum(
                [len(item) for item in results if not isinstance(item, Exception)]
            )
            failed = [item for item in results if isinstance(item, Exception)]
            if failed:
                self._logger.error(
                    f"Failed to kill dead jobs for {len(failed)} scrapers: {failed}"
                )
            if killed > 0:
                self._logger.info(f"Successfully killed {killed} dead jobs")
        except Exception as e:
            self._logger.error(f"Scheduler kill dead jobs failed: {e}")
            self._logger.debug(
                f"Scheduler kill dead jobs failed. Traceback: {format_exc()}"
            )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _delete_old_scraper_jobs(self):
        """Periodic job that cleans up storage from old historical scraper jobs"""
        if not self._is_lease_acquired:
            return
        try:
            self._logger.info("Removing old scraper jobs")
            await self._jobs_storage.delete_old_scraper_jobs(self._jobs_to_keep)
            self._logger.info("Successfully removed old scraper jobs")
        except Exception as e:
            self._logger.error(f"Removing old scraper jobs failed: {e}")
            self._logger.debug(
                f"Removing old scraper jobs failed. Traceback: {format_exc()}"
            )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _export_queue_len(self):
        """Periodic job that exports queue length metrics"""
        if not self._is_lease_acquired:
            return
        try:
            for priority in ScraperJobPriority:
                pending_jobs = await self._queue.get_queue_len(priority)
                queue_length_gauge.labels(priority=priority.name).set(pending_jobs)
        except Exception as e:
            self._logger.error(f"Scheduler export queue length failed: {e}")
            self._logger.debug(
                f"Scheduler export queue length failed. Traceback: {format_exc()}"
            )

    async def start(self) -> None:
        self._logger.info("Starting scheduler")
        self._scheduler.start()

    def stop(self) -> None:
        self._logger.info("Stopping scheduler")
        self._scheduler.shutdown(wait=False)
