from abc import ABC
from datetime import timedelta
from typing import List

from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunPriority


class Storage(ABC):
    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        offset: int | None = None,
    ) -> List[Scraper]:
        raise NotImplementedError()

    async def get_scrapers(self) -> List[Scraper]:
        raise NotImplementedError()

    async def get_scraper(self, id: int) -> Scraper:
        raise NotImplementedError()

    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        raise NotImplementedError()

    async def create_scraper(self, scraper: Scraper) -> Scraper:
        raise NotImplementedError()

    async def update_scraper(self, scraper: Scraper) -> Scraper:
        raise NotImplementedError()

    async def delete_scraper(self, id: int) -> Scraper:
        raise NotImplementedError()

    async def get_scraper_runs(self, scraper_id: int) -> List[ScraperRun]:
        raise NotImplementedError()

    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        raise NotImplementedError()

    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        raise NotImplementedError()

    async def get_scraper_run(self, scraper_id: int, scraper_run_id: int) -> ScraperRun:
        raise NotImplementedError()

    async def dequeue_scraper_run(
        self,
        priority: ScraperRunPriority,
    ) -> ScraperRun | None:
        raise NotImplementedError()

    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        raise NotImplementedError()

    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        raise NotImplementedError()

    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        raise NotImplementedError()
