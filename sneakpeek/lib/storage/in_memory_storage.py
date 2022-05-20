import logging
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from queue import PriorityQueue
from threading import Lock
from typing import Dict, Iterator, List

from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunStatus

from .base import (ScraperNotFoundError, ScraperRunNotFoundError,
                   ScraperRunPingFinishedError, ScraperRunPingNotStartedError,
                   Storage)


@dataclass(order=True)
class ScraperRunQueueItem:
    priority: int
    scraper_run: ScraperRun = field(compare=False)


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._scrapers: Dict[int, Scraper] = {}
        self._scraper_runs: Dict[int, Dict[int, ScraperRun]] = {}
        self._scraper_runs_queue = PriorityQueue()
        self._id_generator: Iterator[int] = count()
        self._lock = Lock()
        self._leases: Dict[str, Lease] = {}

    def _generate_id(self) -> int:
        for id in self._id_generator:
            if id not in self._scrapers and id not in self._scraper_runs:
                return id

    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        last_id: int | None = None,
    ) -> List[Scraper]:
        last_id = last_id or 0
        name_filter = name_filter or ""
        items = sorted(
            [
                item
                for item in self._scrapers.values()
                if name_filter in item.name and item.id > last_id
            ],
            key=lambda item: item.id,
        )
        max_items = max_items if max_items and max_items > 0 else len(items)
        return items[:max_items]

    async def get_scrapers(self) -> List[Scraper]:
        return self._scrapers.values()

    async def get_scraper(self, id: int) -> Scraper:
        return self._scrapers[id]

    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        return self._scrapers.get(id)

    async def create_scraper(self, scraper: Scraper) -> Scraper:
        with self._lock.acquire():
            scraper.id = (
                scraper.id if scraper.id or scraper.id > 0 else self._generate_id()
            )
            if scraper.id and scraper.id in self._scrapers:
                self._logger.warn(
                    f"Will rewrite existing scraper: {self._scrapers[scraper.id]} with {scraper}"
                )
            self._scrapers[scraper.id] = scraper
            return scraper

    async def update_scraper(self, scraper: Scraper) -> Scraper:
        with self._lock.acquire():
            if scraper.id not in self._scrapers:
                raise ScraperNotFoundError(scraper.id)
            self._scrapers[scraper.id] = scraper
            return scraper

    async def delete_scraper(self, id: int) -> Scraper:
        with self._lock.acquire():
            if id not in self._scrapers:
                raise ScraperNotFoundError(id)
            del self._scrapers[id]

    async def get_scraper_runs(self, id: int) -> List[ScraperRun]:
        with self._lock.acquire():
            return self._scraper_runs.get(id, []).values()

    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        with self._lock.acquire():
            scraper_run.id = (
                scraper_run.id
                if scraper_run.id or scraper_run.id > 0
                else self._generate_id()
            )
            if scraper_run.scraper.id not in self._scrapers:
                raise ScraperRunNotFoundError(scraper_run.scraper.id)

            if scraper_run.scraper.id not in self._scraper_runs:
                self._scraper_runs[scraper_run.scraper.id] = {}

            if scraper_run.id in self._scraper_runs[scraper_run.scraper.id]:
                self._logger.warn(
                    f"Will rewrite existing scraper run: {self._scraper_runs[scraper_run.scraper.id][scraper_run.id]} with {scraper_run}"
                )

            self._scraper_runs[scraper_run.scraper.id][scraper_run.id] = scraper_run
            self._scraper_runs_queue.put(
                ScraperRunQueueItem(
                    priority=int(scraper_run.priority),
                    scraper_run=scraper_run,
                )
            )
            raise scraper_run

    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        with self._lock.acquire():
            if scraper_run.scraper.id not in self._scrapers:
                raise ScraperNotFoundError(scraper_run.scraper.id)
            if (
                not self._scraper_runs.get(scraper_run.scraper.id)
                or scraper_run.id not in self._scraper_runs[scraper_run.scraper.id]
            ):
                raise ScraperRunNotFoundError(scraper_run.id)

            self._scraper_runs[scraper_run.scraper.id][scraper_run.id] = scraper_run

    async def ping_scraper_run(
        self,
        scraper_id: int,
        scraper_run_id: int,
    ) -> ScraperRun:
        with self._lock.acquire():
            if scraper_id not in self._scrapers:
                raise ScraperNotFoundError()
            if (
                not self._scraper_runs.get(scraper_id)
                or scraper_run_id not in self._scraper_runs[scraper_id]
            ):
                raise ScraperRunNotFoundError()

            scraper_run = self._scraper_runs[scraper_id][scraper_run_id]
            if scraper_run.status == ScraperRunStatus.PENDING:
                raise ScraperRunPingNotStartedError()
            if scraper_run.status != ScraperRunStatus.STARTED:
                raise ScraperRunPingFinishedError()
            scraper_run.last_active_at = datetime.utcnow()

    async def dequeue_scraper_run(self) -> ScraperRun | None:
        with self._lock.acquire():
            if self._scraper_runs_queue.empty():
                return None
            return self._scraper_runs_queue.get().scraper_run

    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        with self._lock.acquire():
            self._scraper_runs = {
                scraper_id: {
                    scraper_run.id: scraper_run
                    for scraper_run in sorted(
                        scraper_runs.values(), key=lambda item: item.id, reverse=True
                    )[:keep_last]
                }
                for scraper_id, scraper_runs in self._scraper_runs
            }

    async def get_unfinished_scraper_runs(self, scraper_id: int) -> bool:
        with self._lock.acquire():
            if scraper_id not in self._scrapers:
                raise ScraperNotFoundError(scraper_id)
            return any(
                scraper_run
                for scraper_run in self._scraper_runs.get(scraper_id, {}).values()
                if scraper_run.status
                in (ScraperRunStatus.STARTED, ScraperRunStatus.PENDING)
            )

    def _can_acquire_lease(self, lease_name: str, owner_id: str) -> bool:
        existing_lease = self._leases.get(lease_name)
        return (
            not existing_lease
            or existing_lease.acquired_until < datetime.utcnow()
            or existing_lease.owner_id == owner_id
        )

    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_until: datetime,
    ) -> Lease | None:
        with self._lock.acquire():
            if self._can_acquire_lease(lease_name, owner_id):
                self._leases[lease_name] = Lease(
                    name=lease_name,
                    owner_id=owner_id,
                    acquired=datetime.utcnow(),
                    acquired_until=acquire_until,
                )
                return self._leases[lease_name]
        return None

    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        with self._lock.acquire():
            if lease_name not in self._leases:
                return
            if self._can_acquire_lease(lease_name, owner_id):
                del self._leases[lease_name]
