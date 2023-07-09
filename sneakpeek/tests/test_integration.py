import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis
from typing_extensions import override

from sneakpeek.queue.in_memory_storage import InMemoryQueueStorage
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueStorageABC,
    TaskPriority,
    TaskStatus,
)
from sneakpeek.queue.redis_storage import RedisQueueStorage
from sneakpeek.scheduler.in_memory_lease_storage import InMemoryLeaseStorage
from sneakpeek.scheduler.model import LeaseStorageABC, TaskSchedule
from sneakpeek.scheduler.redis_lease_storage import RedisLeaseStorage
from sneakpeek.scraper.in_memory_storage import InMemoryScraperStorage
from sneakpeek.scraper.model import (
    SCRAPER_PERIODIC_TASK_HANDLER_NAME,
    CreateScraperRequest,
    Scraper,
    ScraperConfig,
    ScraperContextABC,
    ScraperHandler,
    ScraperStorageABC,
)
from sneakpeek.scraper.redis_storage import RedisScraperStorage
from sneakpeek.server import SneakpeekServer

SCRAPER_1 = "scraper_1"
SCRAPER_2 = "scraper_2"
TEST_URL = "test_url"
MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN = 2.5
MIN_SECONDS_TO_EXECUTE_RUN = 2.5
HANDLER_NAME = "test_scraper_handler"


class ScraperImpl(ScraperHandler):
    @property
    def name(self) -> str:
        return HANDLER_NAME

    @override
    async def run(self, context: ScraperContextABC) -> str:
        url = (context.params or {}).get("url") or TEST_URL
        await context.get(url)
        return url


@pytest.fixture
def scrapers() -> list[CreateScraperRequest]:
    return [
        CreateScraperRequest(
            name=SCRAPER_1,
            schedule=TaskSchedule.EVERY_SECOND,
            handler=HANDLER_NAME,
            config=ScraperConfig(),
        ),
        CreateScraperRequest(
            name=SCRAPER_2,
            schedule=TaskSchedule.INACTIVE,
            handler=HANDLER_NAME,
            config=ScraperConfig(),
        ),
    ]


Storages = tuple[ScraperStorageABC, QueueStorageABC, LeaseStorageABC]


@pytest.fixture
def in_memory_storage() -> Storages:
    return (
        InMemoryScraperStorage(),
        InMemoryQueueStorage(),
        InMemoryLeaseStorage(),
    )


@pytest.fixture
def redis_storage() -> Storages:
    return (
        RedisScraperStorage(FakeRedis()),
        RedisQueueStorage(FakeRedis()),
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
def server_with_scheduler(
    storages: Storages,
    scrapers: list[Scraper],
) -> SneakpeekServer:
    scraper_storage, queue_storage, lease_storage = storages

    loop = asyncio.get_event_loop()
    for scraper in scrapers:
        loop.run_until_complete(scraper_storage.create_scraper(scraper))

    return SneakpeekServer.create(
        handlers=[ScraperImpl()],
        scraper_storage=scraper_storage,
        queue_storage=queue_storage,
        lease_storage=lease_storage,
        with_web_server=False,
        scheduler_storage_poll_delay=timedelta(milliseconds=100),
    )


@pytest.fixture
def server_with_worker_only(
    storages: Storages,
    scrapers: list[Scraper],
) -> SneakpeekServer:
    scraper_storage, queue_storage, lease_storage = storages

    loop = asyncio.get_event_loop()
    for scraper in scrapers:
        loop.run_until_complete(scraper_storage.create_scraper(scraper))

    return SneakpeekServer.create(
        handlers=[ScraperImpl()],
        scraper_storage=scraper_storage,
        queue_storage=queue_storage,
        lease_storage=lease_storage,
        with_web_server=False,
        with_scheduler=False,
        worker_max_concurrency=1,
        scheduler_storage_poll_delay=timedelta(milliseconds=10),
    )


async def _get_scraper_by_name(
    name: str,
    scraper_storage: ScraperStorageABC,
) -> Scraper:
    scraper = [s for s in await scraper_storage.get_scrapers() if s.name == name]
    assert scraper, f"Couldn't find a scraper '{name}'"
    return scraper[0]


async def _enqueue_task_by_name(
    name: str,
    scraper_storage: ScraperStorageABC,
    server: SneakpeekServer,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> None:
    scraper = await _get_scraper_by_name(name, scraper_storage)
    return await server.consumer.queue.enqueue(
        EnqueueTaskRequest(
            task_name=scraper.id,
            task_handler=SCRAPER_PERIODIC_TASK_HANDLER_NAME,
            priority=priority,
            payload="",
        )
    )


@pytest.mark.asyncio
async def test_scraper_schedules_and_completes(
    server_with_scheduler: SneakpeekServer,
    storages: Storages,
):
    scraper_storage, queue_storage, _ = storages
    try:
        server_with_scheduler.serve(blocking=False)
        with patch("sneakpeek.scraper.context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN)
            scraper = await _get_scraper_by_name(SCRAPER_1, scraper_storage)
            tasks = await queue_storage.get_task_instances(scraper.id)
            assert len(tasks) > 0, "Expected scraper to be run at least once"
            successful_tasks = [
                run for run in tasks if run.status == TaskStatus.SUCCEEDED and run
            ]
            assert (
                len(successful_tasks) > 0
            ), "Expected at least one successful scraper job"
            assert (
                successful_tasks[0].finished_at is not None
            ), "Expected scraper job to have finished ts"
            mocked_request.assert_awaited_with(TEST_URL)
    finally:
        server_with_scheduler.stop()


@pytest.mark.asyncio
async def test_scraper_completes_on_request(
    server_with_worker_only: SneakpeekServer,
    storages: Storages,
):
    scraper_storage, queue_storage, _ = storages
    try:
        server_with_worker_only.serve(blocking=False)
        with patch("sneakpeek.scraper.context.ScraperContext.get") as mocked_request:
            await _enqueue_task_by_name(
                SCRAPER_1, scraper_storage, server_with_worker_only
            )
            await asyncio.sleep(MIN_SECONDS_TO_EXECUTE_RUN)
            scraper = await _get_scraper_by_name(SCRAPER_1, scraper_storage)
            tasks = await queue_storage.get_task_instances(scraper.id)
            assert len(tasks) == 1, "Expected scraper to be run once"
            assert (
                tasks[0].status == TaskStatus.SUCCEEDED
            ), "Expected at least one successful scraper job"
            assert (
                tasks[0].finished_at is not None
            ), "Expected scraper job to have finished ts"
            mocked_request.assert_awaited_once_with(TEST_URL)
    finally:
        server_with_worker_only.stop()


@pytest.mark.asyncio
async def test_tasks_are_executed_according_to_priority(
    server_with_worker_only: SneakpeekServer,
    storages: Storages,
):
    scraper_storage, queue_storage, _ = storages
    try:
        high_pri_job = await _enqueue_task_by_name(
            SCRAPER_1, scraper_storage, server_with_worker_only, TaskPriority.HIGH
        )
        utmost_pri_job = await _enqueue_task_by_name(
            SCRAPER_2, scraper_storage, server_with_worker_only, TaskPriority.UTMOST
        )
        server_with_worker_only.serve(blocking=False)
        with patch("sneakpeek.scraper.context.ScraperContext.get") as mocked_request:
            await asyncio.sleep(MIN_SECONDS_TO_EXECUTE_RUN)
            high_pri_job = await queue_storage.get_task_instance(high_pri_job.id)
            utmost_pri_job = await queue_storage.get_task_instance(utmost_pri_job.id)
            assert high_pri_job.status == TaskStatus.SUCCEEDED
            assert utmost_pri_job.status == TaskStatus.SUCCEEDED
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
    scraper_storage, queue_storage, _ = storages

    # disable all built-in scrapers
    for scraper in await scraper_storage.get_scrapers():
        scraper.schedule = TaskSchedule.INACTIVE
        await scraper_storage.update_scraper(scraper)

    scraper = await _get_scraper_by_name(SCRAPER_1, scraper_storage)

    async def verify_has_successful_job(expected_result: str, timeout: timedelta):
        started = datetime.utcnow()
        deadline = started + timeout
        while True:
            try:
                tasks = await queue_storage.get_task_instances(scraper.id)
                successful_tasks = [
                    j
                    for j in tasks
                    if j.created_at > started
                    and j.result == expected_result
                    and j.status == TaskStatus.SUCCEEDED
                ]
                assert len(successful_tasks) > 0, (
                    f"Expected scraper to have at least one successful "
                    f"job created after {started} within {timeout} with result={expected_result}. "
                    f"Actual scraper tasks: {tasks}"
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
            tasks = await queue_storage.get_task_instances(scraper.id)
            successful_tasks = [
                j
                for j in tasks
                if j.created_at > started
                and j.result == expected_result
                and j.status == TaskStatus.SUCCEEDED
            ]
            assert successful_tasks == []
            await asyncio.sleep(0.1)

    try:
        with patch("sneakpeek.scraper.context.ScraperContext.get"):
            server_with_scheduler.serve(blocking=False)

            # Step 1: Enable scraper and wait for it to be executed
            scraper.schedule = TaskSchedule.EVERY_SECOND
            scraper = await scraper_storage.update_scraper(scraper)
            await verify_has_successful_job(TEST_URL, timedelta(seconds=3))

            # Step 2: Update return value and wait for a job with this value
            scraper.config.params = {"url": "some_other_url"}
            scraper = await scraper_storage.update_scraper(scraper)
            await verify_has_successful_job("some_other_url", timedelta(seconds=3))

            # Step 3: Disable it and make sure there are no tasks at all
            scraper.config.params = {"url": "should_never_be_returned"}
            scraper.schedule = TaskSchedule.INACTIVE
            scraper = await scraper_storage.update_scraper(scraper)
            await asyncio.sleep(0.5)
            await verify_has_no_successful_job(
                "should_never_be_returned",
                timedelta(seconds=MIN_SECONDS_TO_HAVE_1_SUCCESSFUL_RUN),
            )

    finally:
        server_with_scheduler.stop()
