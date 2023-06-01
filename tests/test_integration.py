import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.models import (
    Scraper,
    ScraperJobPriority,
    ScraperJobStatus,
    ScraperSchedule,
)
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.server import SneakpeekServer
from sneakpeek.storage.base import LeaseStorage, ScraperJobsStorage, ScrapersStorage
from sneakpeek.storage.in_memory_storage import (
    InMemoryLeaseStorage,
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.storage.redis_storage import (
    RedisLeaseStorage,
    RedisScraperJobsStorage,
    RedisScrapersStorage,
)

SCRAPER_1_ID = 100000001
SCRAPER_2_ID = 100000002
TEST_URL = "test_url"
MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN = 2.1
MIN_SECONDS_TO_EXECUTE_RUN = 2.1
HANDLER_NAME = "test_scraper_handler"


class ScraperImpl(ScraperHandler):
    @property
    def name(self) -> str:
        return HANDLER_NAME

    async def run(self, context: ScraperContext) -> str:
        url = (context.params or {}).get("url") or TEST_URL
        await context.get(url)
        return url


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
        handlers=[ScraperImpl()],
        scrapers_storage=scrapers_storage,
        jobs_storage=jobs_storage,
        lease_storage=lease_storage,
        with_web_server=False,
        scheduler_storage_poll_delay=timedelta(seconds=1),
    )


@pytest.fixture
def server_with_worker_only(storages: Storages) -> SneakpeekServer:
    scrapers_storage, jobs_storage, lease_storage = storages
    return SneakpeekServer.create(
        handlers=[ScraperImpl()],
        scrapers_storage=scrapers_storage,
        jobs_storage=jobs_storage,
        lease_storage=lease_storage,
        with_web_server=False,
        with_scheduler=False,
        worker_max_concurrency=1,
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


@pytest.mark.asyncio
async def test_scraper_job_updates(
    server_with_scheduler: SneakpeekServer,
    storages: Storages,
):
    scraper_storage, jobs_storage, _ = storages

    # disable all built-in scrapers
    for scraper in await scraper_storage.get_scrapers():
        scraper.schedule = ScraperSchedule.INACTIVE
        await scraper_storage.update_scraper(scraper)

    scraper = await scraper_storage.get_scraper(SCRAPER_1_ID)

    async def verify_has_successful_job(expected_result: str, timeout: timedelta):
        started = datetime.utcnow()
        deadline = started + timeout
        while True:
            try:
                jobs = await jobs_storage.get_scraper_jobs(SCRAPER_1_ID)
                successful_jobs = [
                    j
                    for j in jobs
                    if j.created_at > started
                    and j.result == expected_result
                    and j.status == ScraperJobStatus.SUCCEEDED
                ]
                assert len(successful_jobs) > 0, (
                    f"Expected scraper to have at least one successful "
                    f"job created after {started} within {timeout} with result={expected_result}. "
                    f"Actual scraper jobs: {jobs}"
                )
                return
            except AssertionError:
                if datetime.utcnow() > deadline:
                    raise
            await asyncio.sleep(0.1)

    async def verify_has_no_successful_job(expected_result: str, timeout: timedelta):
        started = datetime.utcnow()
        deadline = started + timeout
        while datetime.utcnow() < deadline:
            jobs = await jobs_storage.get_scraper_jobs(SCRAPER_1_ID)
            successful_jobs = [
                j
                for j in jobs
                if j.created_at > started
                and j.result == expected_result
                and j.status == ScraperJobStatus.SUCCEEDED
            ]
            assert successful_jobs == []
            await asyncio.sleep(0.1)

    try:
        with patch("sneakpeek.scraper_context.ScraperContext.get"):
            server_with_scheduler.serve(blocking=False)

            # Step 1: Enable scraper and wait for it to be executed
            scraper.schedule = ScraperSchedule.EVERY_SECOND
            scraper = await scraper_storage.update_scraper(scraper)
            await verify_has_successful_job(TEST_URL, timedelta(seconds=3))

            # Step 2: Update return value and wait for a job with this value
            scraper.config.params = {"url": "some_other_url"}
            scraper = await scraper_storage.update_scraper(scraper)
            await verify_has_successful_job("some_other_url", timedelta(seconds=3))

            # Step 3: Disable it and make sure there are no jobs at all
            scraper.config.params = {"url": "should_never_be_returned"}
            scraper.schedule = ScraperSchedule.INACTIVE
            scraper = await scraper_storage.update_scraper(scraper)
            await asyncio.sleep(2)
            await verify_has_no_successful_job(
                "should_never_be_returned",
                timedelta(seconds=MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN),
            )

    finally:
        server_with_scheduler.stop()
