import logging
from abc import ABC
from asyncio import Lock
from datetime import datetime, timedelta
from traceback import format_exc
from typing import Dict
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from sneakpeek.lib.models import Lease, Scraper, ScraperSchedule
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage

DEFAULT_LEASE_DURATION = timedelta(minutes=1)
DEFAULT_STORAGE_POLL_DELAY = timedelta(seconds=5)


class SchedulerABC(ABC):
    async def start(self) -> None:
        raise NotImplementedError()

    async def stop(self) -> None:
        raise NotImplementedError()


class Scheduler(SchedulerABC):
    def __init__(
        self,
        storage: Storage,
        queue: QueueABC,
        storage_poll_frequency: timedelta = DEFAULT_STORAGE_POLL_DELAY,
        lease_duration: timedelta = DEFAULT_LEASE_DURATION,
    ) -> None:
        self._lease_name = "sneakpeek:scheduler"
        self._owner_id = str(uuid4())
        self._lease_duration = lease_duration
        self._storage = storage
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

    async def _enqueue_scraper(self, scraper_id: int) -> None:
        scraper = self._scrapers.get(scraper_id)
        if not scraper:
            self._logger.warning(f"Tried to enqueue unknown scraper: {scraper_id}")
            return

        scraper_human_id = f"{scraper.id}:'{scraper.name}'"
        self._logger.debug(f"Trying to enqueue scraper {scraper_human_id}")
        if not self._lease:
            self._logger.debug(
                f"Couldn't enqueue scraper {scraper_human_id} because lease is not acquired"
            )
            return
        try:
            scraper_run = await self._queue.enqueue(
                scraper.id,
                scraper.schedule_priority,
            )
            self._logger.info(
                f"Successfully enqueued scraper {scraper_human_id}: {scraper_run}"
            )
        except Exception as e:
            self._logger.error(f"Failed to enqueue {scraper_human_id}: {e}")
            self._logger.debug(
                f"Failed to enqueue {scraper_human_id}. Traceback: {format_exc()}"
            )

    async def _get_scraper_trigger(self, scraper: Scraper) -> BaseTrigger:
        start_date = datetime.min
        scraper_runs = await self._storage.get_scraper_runs(scraper.id)
        if scraper_runs:
            last_run = sorted(scraper_runs, key=lambda x: x.id, reverse=True)[0]
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

    def _remove_scraper_job(self, scraper) -> None:
        logging.info(f"Removing scraper enqueue job: {scraper}")
        self._scheduler.remove_job(f"scheduler:scraper:{scraper.id}")
        del self._scrapers[scraper.id]

    async def _update_scraper_job(
        self, scraper: Scraper, remove_existing: bool
    ) -> None:
        logging.info(
            f"{'Updating' if remove_existing else 'Adding'} scraper enqueue job: {scraper}"
        )
        job_id = f"scheduler:scraper:{scraper.id}"
        trigger = await self._get_scraper_trigger(scraper)
        self._scrapers[scraper.id] = scraper
        if remove_existing:
            self._scheduler.remove_job(job_id)
        self._scheduler.add_job(
            self._enqueue_scraper,
            trigger,
            id=job_id,
            args=(scraper.id,),
        )

    async def _update_scrapers_jobs(self) -> None:
        scrapers = await self._storage.get_scrapers()
        index = {scraper.id: scraper for scraper in scrapers}
        for existing in self._scrapers.values():
            if existing.id not in index:
                self._remove_scraper_job(existing)
            elif self._scrapers[existing.id] != index[existing.id]:
                await self._update_scraper_job(existing, remove_existing=True)

        for scraper in index.values():
            if scraper.id not in self._scrapers:
                await self._update_scraper_job(scraper, remove_existing=False)

    async def _on_tick(self) -> None:
        self._logger.debug("Starting scheduler update cycle")
        self._logger.debug("Trying to acquire lease")
        self._lease = await self._storage.maybe_acquire_lease(
            self._lease_name,
            self._owner_id,
            self._lease_duration,
        )
        if self._lease:
            self._logger.info(
                f"Successfully acquired lease until {self._lease.acquired_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        await self._update_scrapers_jobs()

    async def start(self) -> None:
        self._logger.info("Starting scheduler")
        self._scheduler.start()

    async def stop(self) -> None:
        self._logger.info("Stopping scheduler")
        self._scheduler.pause()
