import asyncio
from datetime import timedelta
from uuid import uuid4

from typing_extensions import override

from sneakpeek.scraper.model import (
    CreateScraperRequest,
    Scraper,
    ScraperId,
    ScraperNotFoundError,
    ScraperStorageABC,
    StorageIsReadOnlyError,
)


class InMemoryScraperStorage(ScraperStorageABC):
    def __init__(
        self,
        initial_scrapers: list[Scraper] | None = None,
        is_read_only: bool = False,
    ) -> None:
        self.read_only = is_read_only
        self.scrapers: dict[ScraperId, Scraper] = {
            scraper.id: scraper for scraper in initial_scrapers or []
        }
        self.lock = asyncio.Lock()

    @override
    def is_read_only(self) -> bool:
        return self.read_only

    @override
    async def create_scraper(self, request: CreateScraperRequest) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        async with self.lock:
            id = str(uuid4())
            self.scrapers[id] = Scraper(
                id=id,
                name=request.name,
                handler=request.handler,
                schedule=request.schedule,
                schedule_crontab=request.schedule_crontab,
                config=request.config,
                priority=request.priority,
                timeout=(
                    timedelta(seconds=request.timeout_seconds)
                    if request.timeout_seconds
                    else None
                ),
            )
            return self.scrapers[id]

    @override
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        async with self.lock:
            if scraper.id not in self.scrapers:
                raise ScraperNotFoundError()
            self.scrapers[scraper.id] = scraper
            return scraper

    @override
    async def delete_scraper(self, id: ScraperId) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        async with self.lock:
            if id not in self.scrapers:
                raise ScraperNotFoundError()
            return self.scrapers.pop(id)

    @override
    async def get_scraper(self, id: ScraperId) -> Scraper:
        if id not in self.scrapers:
            raise ScraperNotFoundError()
        return self.scrapers[id]

    @override
    async def get_scrapers(self) -> list[Scraper]:
        return list(self.scrapers.values())
