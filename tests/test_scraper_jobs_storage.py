from datetime import datetime

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.models import (
    UNSET_ID,
    Scraper,
    ScraperJob,
    ScraperJobPriority,
    ScraperJobStatus,
    ScraperSchedule,
)
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.storage.base import ScraperJobsStorage, ScrapersStorage
from sneakpeek.storage.in_memory_storage import (
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.storage.redis_storage import RedisScraperJobsStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def scrapers_storage() -> ScrapersStorage:
    return InMemoryScrapersStorage()


@pytest.fixture
def in_memory_storage() -> ScraperJobsStorage:
    return InMemoryScraperJobsStorage()


@pytest.fixture
def redis_storage(scrapers_storage: ScrapersStorage) -> ScraperJobsStorage:
    return RedisScraperJobsStorage(FakeRedis(), scrapers_storage)


storages = [
    pytest.lazy_fixture(in_memory_storage.__name__),
    pytest.lazy_fixture(redis_storage.__name__),
]


def _get_scraper(name: str, id: int = UNSET_ID) -> Scraper:
    return Scraper(
        id=id,
        name=name,
        schedule=ScraperSchedule.CRONTAB,
        schedule_crontab=f"schedule_{name}",
        handler=f"handler_{name}",
        config=ScraperConfig(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("jobs_storage", storages)
async def test_delete_old_scraper_jobs(
    scrapers_storage: ScrapersStorage,
    jobs_storage: ScraperJobsStorage,
):
    scraper = await scrapers_storage.create_scraper(_get_scraper("test_scraper_queue"))
    to_create = 10
    to_keep = 5
    start_id = 0
    for i in range(to_create):
        await jobs_storage.add_scraper_job(
            ScraperJob(
                id=start_id + i,
                scraper=scraper,
                status=ScraperJobStatus.PENDING,
                priority=ScraperJobPriority.NORMAL,
                created_at=datetime(year=2000, month=12, day=31),
            )
        )
    await jobs_storage.delete_old_scraper_jobs(to_keep)
    kept_runs = await jobs_storage.get_scraper_jobs(scraper.id)
    assert len(kept_runs) == to_keep
    for run in kept_runs:
        assert run.id > to_create - to_keep - 1
