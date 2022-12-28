from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List

from prometheus_client import Histogram

from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunPriority

storage_request_latency = Histogram(
    name="storage_request_latency",
    documentation="Time spent processing storage request",
    namespace="sneakpeek",
    subsystem="storage",
    labelnames=["storage", "method"],
)


class Storage(ABC):
    @abstractmethod
    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        offset: int | None = None,
    ) -> List[Scraper]:
        ...

    @abstractmethod
    async def get_scrapers(self) -> List[Scraper]:
        ...

    @abstractmethod
    async def get_scraper(self, id: int) -> Scraper:
        ...

    @abstractmethod
    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        ...

    @abstractmethod
    async def create_scraper(self, scraper: Scraper) -> Scraper:
        ...

    @abstractmethod
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        ...

    @abstractmethod
    async def delete_scraper(self, id: int) -> Scraper:
        ...

    @abstractmethod
    async def get_scraper_runs(self, scraper_id: int) -> List[ScraperRun]:
        ...

    @abstractmethod
    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        ...

    @abstractmethod
    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        ...

    @abstractmethod
    async def get_scraper_run(self, scraper_id: int, scraper_run_id: int) -> ScraperRun:
        ...

    @abstractmethod
    async def dequeue_scraper_run(
        self,
        priority: ScraperRunPriority,
    ) -> ScraperRun | None:
        ...

    @abstractmethod
    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        ...

    @abstractmethod
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        ...

    @abstractmethod
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        ...
