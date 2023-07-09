from datetime import timedelta
from uuid import uuid4

from redis.asyncio import Redis
from typing_extensions import override

from sneakpeek.scraper.model import (
    CreateScraperRequest,
    Scraper,
    ScraperId,
    ScraperNotFoundError,
    ScraperStorageABC,
    StorageIsReadOnlyError,
)

_SCRAPER_KEY_PREFIX = "scraper:"


class RedisScraperStorage(ScraperStorageABC):
    def __init__(self, redis: Redis, is_read_only: bool = False) -> None:
        self.redis = redis
        self.read_only = is_read_only

    def _get_scraper_key(self, id: ScraperId) -> str:
        return f"{_SCRAPER_KEY_PREFIX}{id}"

    @override
    def is_read_only(self) -> bool:
        return self.read_only

    @override
    async def create_scraper(self, request: CreateScraperRequest) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        scraper = Scraper(
            id=str(uuid4()),
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
        await self.redis.set(self._get_scraper_key(scraper.id), scraper.json())
        return scraper

    @override
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        if not await self.redis.exists(self._get_scraper_key(scraper.id)):
            raise ScraperNotFoundError()
        await self.redis.set(self._get_scraper_key(scraper.id), scraper.json())
        return scraper

    @override
    async def delete_scraper(self, id: ScraperId) -> Scraper:
        if self.read_only:
            raise StorageIsReadOnlyError()
        scraper = await self.redis.getdel(self._get_scraper_key(id))
        if not scraper:
            raise ScraperNotFoundError()
        return Scraper.parse_raw(scraper)

    @override
    async def get_scraper(self, id: ScraperId) -> Scraper:
        scraper = await self.redis.get(self._get_scraper_key(id))
        if scraper is None:
            raise ScraperNotFoundError()
        return Scraper.parse_raw(scraper)

    @override
    async def get_scrapers(self) -> list[Scraper]:
        keys = [
            key.decode()
            async for key in self.redis.scan_iter(f"{_SCRAPER_KEY_PREFIX}*")
        ]
        return sorted(
            (Scraper.parse_raw(scraper) for scraper in await self.redis.mget(keys)),
            key=lambda x: x.id,
        )
