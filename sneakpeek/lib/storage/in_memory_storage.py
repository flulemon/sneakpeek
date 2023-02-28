import logging
from asyncio import Lock
from datetime import datetime, timedelta
from itertools import count
from typing import Iterator

from sneakpeek.lib.errors import ScraperNotFoundError, ScraperRunNotFoundError
from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunPriority
from sneakpeek.metrics import count_invocations, measure_latency

from .base import Storage


class InMemoryStorage(Storage):
    def __init__(
        self,
        scrapers: list[Scraper] | None = None,
        is_read_only: bool = False,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._scrapers: dict[int, Scraper] = {
            scraper.id: scraper for scraper in scrapers or []
        }
        self._scraper_runs: dict[int, dict[int, ScraperRun]] = {}
        self._queues: dict[ScraperRunPriority, list[ScraperRun]] = {}
        self._id_generator: Iterator[int] = count(1)
        self._lock = Lock()
        self._leases: dict[str, Lease] = {}
        self._is_read_only = is_read_only

    def _generate_id(self) -> int:
        for id in self._id_generator:
            if id not in self._scrapers and id not in self._scraper_runs:
                return id

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

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_runs(self, id: int) -> list[ScraperRun]:
        async with self._lock:
            if id not in self._scrapers:
                raise ScraperNotFoundError(id)
            return list(
                sorted(
                    self._scraper_runs.get(id, {}).values(),
                    key=lambda x: x.id,
                    reverse=True,
                )
            )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        async with self._lock:
            scraper_run.id = (
                scraper_run.id
                if scraper_run.id and scraper_run.id > 0
                else self._generate_id()
            )
            if scraper_run.scraper.id not in self._scrapers:
                raise ScraperRunNotFoundError(scraper_run.scraper.id)

            if scraper_run.scraper.id not in self._scraper_runs:
                self._scraper_runs[scraper_run.scraper.id] = {}

            if scraper_run.id in self._scraper_runs[scraper_run.scraper.id]:
                self._logger.warning(
                    f"Will rewrite existing scraper run: {self._scraper_runs[scraper_run.scraper.id][scraper_run.id]} with {scraper_run}"
                )

            self._scraper_runs[scraper_run.scraper.id][scraper_run.id] = scraper_run
            if scraper_run.priority not in self._queues:
                self._queues[scraper_run.priority] = []
            self._queues[scraper_run.priority].append(scraper_run)
            return scraper_run

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        async with self._lock:
            if scraper_run.scraper.id not in self._scrapers:
                raise ScraperNotFoundError(scraper_run.scraper.id)
            if (
                not self._scraper_runs.get(scraper_run.scraper.id)
                or scraper_run.id not in self._scraper_runs[scraper_run.scraper.id]
            ):
                raise ScraperRunNotFoundError(scraper_run.id)

            self._scraper_runs[scraper_run.scraper.id][scraper_run.id] = scraper_run
            return scraper_run

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_run(self, scraper_id: int, scraper_run_id: int) -> ScraperRun:
        async with self._lock:
            if scraper_id not in self._scrapers:
                raise ScraperNotFoundError(scraper_id)
            if (
                not self._scraper_runs.get(scraper_id)
                or scraper_run_id not in self._scraper_runs[scraper_id]
            ):
                raise ScraperRunNotFoundError(scraper_run_id)
            return self._scraper_runs[scraper_id][scraper_run_id]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def dequeue_scraper_run(
        self,
        priority: ScraperRunPriority,
    ) -> ScraperRun | None:
        async with self._lock:
            if not self._queues.get(priority):
                return None
            return self._queues[priority].pop(0)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_queue_len(self, priority: ScraperRunPriority) -> int:
        return len(self._queues.get(priority) or [])

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        async with self._lock:
            self._scraper_runs = {
                scraper_id: {
                    scraper_run.id: scraper_run
                    for scraper_run in sorted(
                        scraper_runs.values(),
                        key=lambda item: item.id,
                        reverse=True,
                    )[:keep_last]
                }
                for scraper_id, scraper_runs in self._scraper_runs.items()
            }

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

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def is_read_only(self) -> bool:
        return self._is_read_only
