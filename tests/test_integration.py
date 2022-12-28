import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.lib.models import (
    Scraper,
    ScraperRunPriority,
    ScraperRunStatus,
    ScraperSchedule,
)
from sneakpeek.lib.storage.base import Storage
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
from sneakpeek.lib.storage.redis_storage import RedisStorage
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.server import SneakpeekServer

SCRAPER_1_ID = 100000001
SCRAPER_2_ID = 100000002
TEST_URL = "test_url"
MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN = 3
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


@pytest.fixture
def in_memory_storage(scrapers: list[Scraper]) -> Storage:
    return InMemoryStorage(scrapers=scrapers)


@pytest.fixture
def redis_storage(scrapers: list[Scraper]) -> Storage:
    storage = RedisStorage(FakeRedis())
    loop = asyncio.get_event_loop()
    for scraper in scrapers:
        loop.run_until_complete(storage.create_scraper(scraper))
    return storage


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def storage(request) -> Storage:
    return request.param


@pytest.fixture
def server_with_scheduler(storage: Storage) -> SneakpeekServer:
    return SneakpeekServer(
        handlers=[TestScraper()],
        storage=storage,
        run_api=False,
        scheduler_storage_poll_delay=timedelta(seconds=1),
        expose_metrics=False,
    )


@pytest.fixture
def server_with_worker_only(storage: Storage) -> SneakpeekServer:
    return SneakpeekServer(
        handlers=[TestScraper()],
        storage=storage,
        run_api=False,
        run_scheduler=False,
        worker_max_concurrency=1,
        expose_metrics=False,
    )


@pytest.mark.asyncio
async def test_scraper_schedules_and_completes(
    server_with_scheduler: SneakpeekServer,
    storage: Storage,
):
    try:
        await server_with_scheduler.start()
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN)
            runs = await storage.get_scraper_runs(SCRAPER_1_ID)
            assert len(runs) > 0, "Expected scraper to be run at least once"
            successful_runs = [
                run for run in runs if run.status == ScraperRunStatus.SUCCEEDED
            ]
            assert (
                len(successful_runs) > 0
            ), "Expected at least one successful scraper run"
            assert (
                successful_runs[0].finished_at is not None
            ), "Expected scraper run to have finished ts"
            mocked_request.assert_awaited_with(TEST_URL)
    finally:
        await server_with_scheduler.stop()


@pytest.mark.asyncio
async def test_scraper_completes_on_request(
    server_with_worker_only: SneakpeekServer,
    storage: Storage,
):
    try:
        await server_with_worker_only.start()
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await server_with_worker_only._queue.enqueue(
                SCRAPER_1_ID,
                ScraperRunPriority.HIGH,
            )
            await asyncio.sleep(2)
            runs = await storage.get_scraper_runs(SCRAPER_1_ID)
            assert len(runs) == 1, "Expected scraper to be run once"
            assert (
                runs[0].status == ScraperRunStatus.SUCCEEDED
            ), "Expected at least one successful scraper run"
            assert (
                runs[0].finished_at is not None
            ), "Expected scraper run to have finished ts"
            mocked_request.assert_awaited_once_with(TEST_URL)
    finally:
        await server_with_worker_only.stop()


@pytest.mark.asyncio
async def test_runs_are_executed_according_to_priority(
    server_with_worker_only: SneakpeekServer,
    storage: Storage,
):
    try:
        high_pri_job = await server_with_worker_only._queue.enqueue(
            SCRAPER_1_ID,
            ScraperRunPriority.HIGH,
        )
        utmost_pri_job = await server_with_worker_only._queue.enqueue(
            SCRAPER_2_ID,
            ScraperRunPriority.UTMOST,
        )
        await server_with_worker_only.start()
        with patch("sneakpeek.scraper_context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(3)
            high_pri_job = await storage.get_scraper_run(SCRAPER_1_ID, high_pri_job.id)
            utmost_pri_job = await storage.get_scraper_run(
                SCRAPER_2_ID, utmost_pri_job.id
            )
            assert high_pri_job.status == ScraperRunStatus.SUCCEEDED
            assert utmost_pri_job.status == ScraperRunStatus.SUCCEEDED
            assert utmost_pri_job.finished_at < high_pri_job.finished_at
            assert mocked_request.call_count == 2
            mocked_request.assert_awaited_with(TEST_URL)
    finally:
        await server_with_worker_only.stop()
