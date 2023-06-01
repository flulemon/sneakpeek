import logging
from asyncio import Lock
from datetime import datetime, timedelta
from itertools import count
from typing import Iterator

from sneakpeek.errors import ScraperJobNotFoundError, ScraperNotFoundError
from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.models import Lease, Scraper, ScraperJob, ScraperJobPriority
from sneakpeek.storage.base import LeaseStorage, ScraperJobsStorage, ScrapersStorage


class InMemoryScrapersStorage(ScrapersStorage):
    """In-memory storage implementation"""

    def __init__(
        self,
        scrapers: list[Scraper] | None = None,
        is_read_only: bool = True,
    ) -> None:
        """
        Args:
            scrapers (list[Scraper] | None, optional): List of pre-defined scrapers. Defaults to None.
            is_read_only (bool, optional): Whether to allow modifications of the scrapers list. Set to true only for development. Defaults to True.
        """
        self._logger = logging.getLogger(__name__)
        self._scrapers: dict[int, Scraper] = {
            scraper.id: scraper for scraper in scrapers or []
        }
        self._id_generator: Iterator[int] = count(1)
        self._lock = Lock()
        self._is_read_only = is_read_only

    def _generate_id(self) -> int:
        for id in self._id_generator:
            if id not in self._scrapers:
                return id

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def is_read_only(self) -> bool:
        return self._is_read_only

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        offset: int | None = None,
    ) -> list[Scraper]:
        offset = offset or 0
        name_filter = name_filter or ""
        items = sorted(
            [
                item
                for item in self._scrapers.values()
                if name_filter in item.name and item.id > offset
            ],
            key=lambda item: item.id,
        )
        max_items = max_items if max_items and max_items > 0 else len(items)
        return items[:max_items]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scrapers(self) -> list[Scraper]:
        return list(self._scrapers.values())

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper(self, id: int) -> Scraper:
        if id not in self._scrapers:
            raise ScraperNotFoundError(id)
        return self._scrapers[id]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        return self._scrapers.get(id)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def create_scraper(self, scraper: Scraper) -> Scraper:
        async with self._lock:
            scraper.id = (
                scraper.id if scraper.id and scraper.id > 0 else self._generate_id()
            )
            if scraper.id and scraper.id in self._scrapers:
                self._logger.warning(
                    f"Will rewrite existing scraper: {self._scrapers[scraper.id]} with {scraper}"
                )
            self._scrapers[scraper.id] = scraper
            return scraper

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        async with self._lock:
            if scraper.id not in self._scrapers:
                raise ScraperNotFoundError(scraper.id)
            self._scrapers[scraper.id] = scraper
            return scraper

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def delete_scraper(self, id: int) -> Scraper:
        async with self._lock:
            if id not in self._scrapers:
                raise ScraperNotFoundError(id)
            scraper_to_delete = self._scrapers[id]
            del self._scrapers[id]
            return scraper_to_delete


class InMemoryScraperJobsStorage(ScraperJobsStorage):
    """In memory storage for scraper jobs. Should only be used for development purposes"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._scraper_jobs: dict[int, dict[int, ScraperJob]] = {}
        self._queues: dict[ScraperJobPriority, list[ScraperJob]] = {}
        self._id_generator: Iterator[int] = count(1)
        self._lock = Lock()

    def _generate_id(self) -> int:
        for id in self._id_generator:
            for scraper_id, scraper_jobs in self._scraper_jobs.items():
                if id == scraper_id or id in scraper_jobs:
                    continue
            return id

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_jobs(self, id: int) -> list[ScraperJob]:
        async with self._lock:
            return list(
                sorted(
                    self._scraper_jobs.get(id, {}).values(),
                    key=lambda x: x.id,
                    reverse=True,
                )
            )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def add_scraper_job(self, scraper_job: ScraperJob) -> ScraperJob:
        async with self._lock:
            scraper_job.id = (
                scraper_job.id
                if scraper_job.id and scraper_job.id > 0
                else self._generate_id()
            )

            if scraper_job.scraper.id not in self._scraper_jobs:
                self._scraper_jobs[scraper_job.scraper.id] = {}

            if scraper_job.id in self._scraper_jobs[scraper_job.scraper.id]:
                self._logger.warning(
                    f"Will rewrite existing scraper run: {self._scraper_jobs[scraper_job.scraper.id][scraper_job.id]} with {scraper_job}"
                )

            self._scraper_jobs[scraper_job.scraper.id][scraper_job.id] = scraper_job
            if scraper_job.priority not in self._queues:
                self._queues[scraper_job.priority] = []
            self._queues[scraper_job.priority].append(scraper_job)
            return scraper_job

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def update_scraper_job(self, scraper_job: ScraperJob) -> ScraperJob:
        async with self._lock:
            if (
                not self._scraper_jobs.get(scraper_job.scraper.id)
                or scraper_job.id not in self._scraper_jobs[scraper_job.scraper.id]
            ):
                raise ScraperJobNotFoundError(scraper_job.id)

            self._scraper_jobs[scraper_job.scraper.id][scraper_job.id] = scraper_job
            return scraper_job

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_job(self, scraper_id: int, scraper_job_id: int) -> ScraperJob:
        async with self._lock:
            if (
                not self._scraper_jobs.get(scraper_id)
                or scraper_job_id not in self._scraper_jobs[scraper_id]
            ):
                raise ScraperJobNotFoundError(scraper_job_id)
            return self._scraper_jobs[scraper_id][scraper_job_id]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def dequeue_scraper_job(
        self,
        priority: ScraperJobPriority,
    ) -> ScraperJob | None:
        async with self._lock:
            if not self._queues.get(priority):
                return None
            return self._queues[priority].pop(0)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_queue_len(self, priority: ScraperJobPriority) -> int:
        return len(self._queues.get(priority) or [])

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def delete_old_scraper_jobs(self, keep_last: int = 50) -> None:
        async with self._lock:
            self._scraper_jobs = {
                scraper_id: {
                    scraper_job.id: scraper_job
                    for scraper_job in sorted(
                        scraper_jobs.values(),
                        key=lambda item: item.id,
                        reverse=True,
                    )[:keep_last]
                }
                for scraper_id, scraper_jobs in self._scraper_jobs.items()
            }


class InMemoryLeaseStorage(LeaseStorage):
    """In memory storage for leases. Should only be used for development purposes"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._lock = Lock()
        self._leases: dict[str, Lease] = {}

    def _can_acquire_lease(self, lease_name: str, owner_id: str) -> bool:
        existing_lease = self._leases.get(lease_name)
        return (
            not existing_lease
            or existing_lease.acquired_until < datetime.utcnow()
            or existing_lease.owner_id == owner_id
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        async with self._lock:
            if self._can_acquire_lease(lease_name, owner_id):
                self._leases[lease_name] = Lease(
                    name=lease_name,
                    owner_id=owner_id,
                    acquired=datetime.utcnow(),
                    acquired_until=datetime.utcnow() + acquire_for,
                )
                return self._leases[lease_name]
        return None

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        async with self._lock:
            if lease_name not in self._leases:
                return
            if self._can_acquire_lease(lease_name, owner_id):
                del self._leases[lease_name]
