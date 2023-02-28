from datetime import datetime, timedelta
from typing import List

from redis.asyncio import Redis

from sneakpeek.lib.errors import ScraperNotFoundError, ScraperRunNotFoundError
from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunPriority
from sneakpeek.metrics import count_invocations, measure_latency

from .base import Storage


class RedisStorage(Storage):
    def __init__(
        self,
        redis: Redis,
        is_read_only: bool = False,
    ) -> None:
        self._redis = redis
        self._is_read_only = is_read_only

    async def _generate_id(self) -> int:
        return int(await self._redis.incr("internal:id_counter"))

    async def _generate_queue_id(self, priority: ScraperRunPriority) -> int:
        return int(await self._redis.incr(f"internal:queue:{priority}:last_id"))

    async def _get_queue_last_id(self, priority: ScraperRunPriority) -> int:
        return int(await self._redis.get(f"internal:queue:{priority}:last_id") or 0)

    async def _get_queue_offset(self, priority: ScraperRunPriority) -> int:
        return int(await self._redis.get(f"internal:queue:{priority}:offset") or 0)

    def _get_scraper_key(self, id: int) -> str:
        return f"scraper:{id}"

    def _get_scraper_run_key(self, scraper_id: int, run_id: int) -> str:
        return f"scraper_run:{scraper_id}:{run_id}"

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        offset: int | None = None,
    ) -> List[Scraper]:
        start = offset or 0
        end = start + (max_items or 10)
        return [
            scraper
            for scraper in await self.get_scrapers()
            if name_filter in scraper.name
        ][start:end]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scrapers(self) -> List[Scraper]:
        keys = [key.decode() async for key in self._redis.scan_iter("scraper:*")]
        return sorted(
            (Scraper.parse_raw(scraper) for scraper in await self._redis.mget(keys)),
            key=lambda x: x.id,
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper(self, id: int) -> Scraper:
        scraper = await self.maybe_get_scraper(id)
        if not scraper:
            raise ScraperNotFoundError()
        return scraper

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        scraper = await self._redis.get(f"scraper:{id}")
        return Scraper.parse_raw(scraper) if scraper else None

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def create_scraper(self, scraper: Scraper) -> Scraper:
        scraper.id = (
            scraper.id if scraper.id and scraper.id > 0 else await self._generate_id()
        )
        await self._redis.set(self._get_scraper_key(scraper.id), scraper.json())
        return scraper

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        if not await self._redis.exists(self._get_scraper_key(scraper.id)):
            raise ScraperNotFoundError()
        await self._redis.set(self._get_scraper_key(scraper.id), scraper.json())
        return scraper

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def delete_scraper(self, id: int) -> Scraper:
        scraper = await self._redis.getdel(self._get_scraper_key(id))
        if not scraper:
            raise ScraperNotFoundError()
        return Scraper.parse_raw(scraper)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_runs(self, scraper_id: int) -> List[ScraperRun]:
        keys = [
            key.decode()
            async for key in self._redis.scan_iter(f"scraper_run:{scraper_id}:*")
        ]
        return sorted(
            [ScraperRun.parse_raw(run) for run in await self._redis.mget(keys)],
            key=lambda x: x.id,
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        if not await self._redis.exists(f"scraper:{scraper_run.scraper.id}"):
            raise ScraperNotFoundError()
        scraper_run.id = (
            scraper_run.id
            if scraper_run.id and scraper_run.id > 0
            else await self._generate_id()
        )
        job_id = await self._generate_queue_id(scraper_run.priority)

        pipeline = self._redis.pipeline()
        pipeline.set(
            self._get_scraper_run_key(scraper_run.scraper.id, scraper_run.id),
            scraper_run.json(),
        )
        pipeline.set(
            f"queue:{scraper_run.priority}:{job_id}",
            scraper_run.json(),
        )
        await pipeline.execute()

        return scraper_run

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        if not await self._redis.exists(self._get_scraper_key(scraper_run.scraper.id)):
            raise ScraperNotFoundError()
        if not await self._redis.exists(
            self._get_scraper_run_key(scraper_run.scraper.id, scraper_run.id)
        ):
            raise ScraperRunNotFoundError()
        await self._redis.set(
            self._get_scraper_run_key(scraper_run.scraper.id, scraper_run.id),
            scraper_run.json(),
        )
        return scraper_run

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def dequeue_scraper_run(
        self, priority: ScraperRunPriority
    ) -> ScraperRun | None:
        offset = await self._get_queue_offset(priority)
        last_id = await self._get_queue_last_id(priority)
        if offset < last_id:
            pipeline = self._redis.pipeline()
            pipeline.getdel(f"queue:{priority}:{offset+1}")
            pipeline.incr(f"internal:queue:{priority}:offset")
            run, _ = await pipeline.execute()
            return ScraperRun.parse_raw(run)
        return None

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_queue_len(self, priority: ScraperRunPriority) -> int:
        offset = await self._get_queue_offset(priority)
        last_id = await self._get_queue_last_id(priority)
        return last_id - offset

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        to_delete = []
        for scraper in await self.get_scrapers():
            runs = await self.get_scraper_runs(scraper.id)
            if len(runs) > keep_last:
                to_delete += [
                    self._get_scraper_run_key(scraper.id, run.id)
                    for run in runs[:-keep_last]
                ]
        await self._redis.delete(*to_delete)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def get_scraper_run(self, scraper_id: int, scraper_run_id: int) -> ScraperRun:
        if not await self._redis.exists(self._get_scraper_key(scraper_id)):
            raise ScraperNotFoundError()
        scraper_run = await self._redis.get(
            self._get_scraper_run_key(scraper_id, scraper_run_id),
        )
        if not scraper_run:
            raise ScraperRunNotFoundError()
        return ScraperRun.parse_raw(scraper_run)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        lease_key = f"lease:{lease_name}"
        existing_lease = await self._redis.get(lease_key)
        result = None
        if not existing_lease or existing_lease.decode() == owner_id:
            result = await self._redis.set(
                f"lease:{lease_name}",
                owner_id,
                ex=acquire_for,
            )
        return (
            Lease(
                name=lease_name,
                owner_id=owner_id,
                acquired=datetime.utcnow(),
                acquired_until=datetime.utcnow() + acquire_for,
            )
            if result
            else None
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        lease_owner = await self._redis.get(f"lease:{lease_name}")
        if lease_owner == owner_id:
            await self._redis.delete(f"lease:{lease_name}")

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def is_read_only(self) -> bool:
        return self._is_read_only
