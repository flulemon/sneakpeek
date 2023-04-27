import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.lib.models import (
    Scraper,
    ScraperJobPriority,
    ScraperJobStatus,
    ScraperSchedule,
)
from sneakpeek.lib.storage.base import LeaseStorage, ScraperJobsStorage, ScrapersStorage
from sneakpeek.lib.storage.in_memory_storage import (
    InMemoryLeaseStorage,
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.lib.storage.redis_storage import (
    RedisLeaseStorage,
    RedisScraperJobsStorage,
    RedisScrapersStorage,
)
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.server import SneakpeekServer

SCRAPER_1_ID = 100000001
SCRAPER_2_ID = 100000002
TEST_URL = "test_url"
MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN = 2.1
MIN_SECONDS_TO_EXECUTE_RUN = 2.1
HANDLER_NAME = "test_scraper_handler"


class TestScraper(ScraperHandler):
    @property
    def name(self) -> str:
        return HANDLER_NAME

    async def run(self, context: ScraperContext) -> str:
        await context.get(TEST_URL)


@pytest.fixture
def scrapers() -> list[Scraper]:
    return [
        Scraper(
            id=SCRAPER_1_ID,
            name="active_scraper",
            schedule=ScraperSchedule.EVERY_SECOND,
            handler=HANDLER_NAME,
            config=ScraperConfig(),
        ),
        Scraper(
            id=SCRAPER_2_ID,
            name="inactive_scraper",
            schedule=ScraperSchedule.INACTIVE,
            handler=HANDLER_NAME,
            config=ScraperConfig(),
        ),
    ]


Storages = tuple[ScrapersStorage, ScraperJobsStorage, LeaseStorage]


@pytest.fixture
def in_memory_storage(scrapers: list[Scraper]) -> Storages:
    return (
        InMemoryScrapersStorage(scrapers=scrapers),
        InMemoryScraperJobsStorage(),
        InMemoryLeaseStorage(),
    )


@pytest.fixture
def redis_storage(scrapers: list[Scraper]) -> Storages:
    scrapers_storage = RedisScrapersStorage(FakeRedis())
    loop = asyncio.get_event_loop()
    for scraper in scrapers:
        loop.run_until_complete(scrapers_storage.create_scraper(scraper))
    return (
        scrapers_storage,
        RedisScraperJobsStorage(FakeRedis(), scrapers_storage),
        RedisLeaseStorage(FakeRedis()),
    )


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def storages(request) -> Storages:
    return request.param


@pytest.fixture
def server_with_scheduler(storages: Storages) -> SneakpeekServer:
    scrapers_storage, jobs_storage, lease_storage = storages
    return SneakpeekServer.create(
        handlers=[TestScraper()],
        scrapers_storage=scrapers_storage,
        jobs_storage=jobs_storage,
        lease_storage=lease_storage,
        with_api=False,
        scheduler_storage_poll_delay=timedelta(seconds=1),
        expose_metrics=False,
    )


@pytest.fixture
def server_with_worker_only(storages: Storages) -> SneakpeekServer:
    scrapers_storage, jobs_storage, lease_storage = storages
    return SneakpeekServer.create(
        handlers=[TestScraper()],
        scrapers_storage=scrapers_storage,
        jobs_storage=jobs_storage,
        lease_storage=lease_storage,
        with_api=False,
        with_scheduler=False,
        worker_max_concurrency=1,
        expose_metrics=False,
    )


@pytest.mark.asyncio
async def test_scraper_schedules_and_completes(
    server_with_scheduler: SneakpeekServer,
    storages: Storages,
):
    _, jobs_storage, _ = storages
    try:
        server_with_scheduler.serve(blocking=False)
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN)
            jobs = await jobs_storage.get_scraper_jobs(SCRAPER_1_ID)
            assert len(jobs) > 0, "Expected scraper to be run at least once"
            successful_jobs = [
                run for run in jobs if run.status == ScraperJobStatus.SUCCEEDED
            ]
            assert (
                len(successful_jobs) > 0
            ), "Expected at least one successful scraper job"
            assert (
                successful_jobs[0].finished_at is not None
            ), "Expected scraper job to have finished ts"
            mocked_request.assert_awaited_with(TEST_URL)
    finally:
        server_with_scheduler.stop()


@pytest.mark.asyncio
async def test_scraper_completes_on_request(
    server_with_worker_only: SneakpeekServer,
    storages: Storages,
):
    _, jobs_storage, _ = storages
    try:
        server_with_worker_only.serve(blocking=False)
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await server_with_worker_only.worker._queue.enqueue(
                SCRAPER_1_ID,
                ScraperJobPriority.HIGH,
            )
            await asyncio.sleep(MIN_SECONDS_TO_EXECUTE_RUN)
            jobs = await jobs_storage.get_scraper_jobs(SCRAPER_1_ID)
            assert len(jobs) == 1, "Expected scraper to be run once"
            assert (
                jobs[0].status == ScraperJobStatus.SUCCEEDED
            ), "Expected at least one successful scraper job"
            assert (
                jobs[0].finished_at is not None
            ), "Expected scraper job to have finished ts"
            mocked_request.assert_awaited_once_with(TEST_URL)
    finally:
        server_with_worker_only.stop()


@pytest.mark.asyncio
async def test_jobs_are_executed_according_to_priority(
    server_with_worker_only: SneakpeekServer,
    storages: Storages,
):
    _, jobs_storage, _ = storages
    try:
        high_pri_job = await server_with_worker_only.worker._queue.enqueue(
            SCRAPER_1_ID,
            ScraperJobPriority.HIGH,
        )
        utmost_pri_job = await server_with_worker_only.worker._queue.enqueue(
            SCRAPER_2_ID,
            ScraperJobPriority.UTMOST,
        )
        server_with_worker_only.serve(blocking=False)
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(MIN_SECONDS_TO_EXECUTE_RUN)
            high_pri_job = await jobs_storage.get_scraper_job(
                SCRAPER_1_ID, high_pri_job.id
            )
            utmost_pri_job = await jobs_storage.get_scraper_job(
                SCRAPER_2_ID, utmost_pri_job.id
            )
            assert high_pri_job.status == ScraperJobStatus.SUCCEEDED
            assert utmost_pri_job.status == ScraperJobStatus.SUCCEEDED
            assert utmost_pri_job.finished_at < high_pri_job.finished_at
            assert mocked_request.call_count == 2
            mocked_request.assert_awaited_with(TEST_URL)
    finally:
        server_with_worker_only.stop()
