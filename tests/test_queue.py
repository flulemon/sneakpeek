from datetime import datetime

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.lib.errors import (
    ScraperHasActiveRunError,
    ScraperJobPingFinishedError,
    ScraperJobPingNotStartedError,
)
from sneakpeek.lib.models import (
    UNSET_ID,
    Scraper,
    ScraperJobPriority,
    ScraperJobStatus,
    ScraperSchedule,
)
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.base import ScraperJobsStorage, ScrapersStorage
from sneakpeek.lib.storage.in_memory_storage import (
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.lib.storage.redis_storage import RedisScraperJobsStorage
from sneakpeek.scraper_config import ScraperConfig

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


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def jobs_storage(request) -> ScraperJobsStorage:
    return request.param


def _get_scraper(name: str, id: int = UNSET_ID) -> Scraper:
    return Scraper(
        id=id,
        name=name,
        schedule=ScraperSchedule.CRONTAB,
        schedule_crontab=f"schedule_{name}",
        handler="handler_{name}",
        config=ScraperConfig(),
    )


@pytest.mark.asyncio
async def test_enqueue_dequeue(
    scrapers_storage: ScrapersStorage, jobs_storage: ScrapersStorage
):
    queue = Queue(scrapers_storage, jobs_storage)
    scraper = await scrapers_storage.create_scraper(
        _get_scraper("test_enqueue_dequeue")
    )
    enqueued = await queue.enqueue(scraper.id, ScraperJobPriority.NORMAL)
    dequeued = await queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == enqueued.id
    assert dequeued.scraper.id == enqueued.scraper.id
    assert dequeued.status == ScraperJobStatus.STARTED
    assert dequeued.started_at is not None


@pytest.mark.asyncio
async def test_double_enqueue_forbidden(
    scrapers_storage: ScrapersStorage, jobs_storage: ScrapersStorage
):
    queue = Queue(scrapers_storage, jobs_storage)
    scraper = await scrapers_storage.create_scraper(
        _get_scraper("test_double_enqueue_forbidden")
    )
    await queue.enqueue(scraper.id, ScraperJobPriority.NORMAL)
    with pytest.raises(ScraperHasActiveRunError):
        await queue.enqueue(scraper.id, ScraperJobPriority.NORMAL)


@pytest.mark.asyncio
async def test_enqueue_count_equals_dequeue_count(
    scrapers_storage: ScrapersStorage, jobs_storage: ScrapersStorage
):
    queue = Queue(scrapers_storage, jobs_storage)
    expected = []
    tasks_to_enqueue = 10
    for i in range(tasks_to_enqueue):
        scraper = await scrapers_storage.create_scraper(
            _get_scraper(f"test_enqueue_order_{i}")
        )
        enqueued = await queue.enqueue(scraper.id, ScraperJobPriority.NORMAL)
        expected.append(enqueued.id)

    dequeued = []
    for i in range(tasks_to_enqueue):
        dequeued.append((await queue.dequeue()).id)
    assert dequeued == expected
    await queue.dequeue() is None


@pytest.mark.asyncio
async def test_scraper_queue(
    scrapers_storage: ScrapersStorage, jobs_storage: ScrapersStorage
):
    queue = Queue(scrapers_storage, jobs_storage)
    created_scraper = await scrapers_storage.create_scraper(
        _get_scraper("test_scraper_queue")
    )
    created_run = await queue.enqueue(created_scraper.id, ScraperJobPriority.UTMOST)
    assert created_run.id >= 0, "Expected scraper run ID to be positive or zero"
    assert created_run.scraper == created_scraper
    assert created_run.status == ScraperJobStatus.PENDING
    actual_run = await jobs_storage.get_scraper_jobs(created_scraper.id)
    assert actual_run == [created_run]
    with pytest.raises(ScraperJobPingNotStartedError):
        await queue.ping_scraper_job(created_scraper.id, created_run.id)
    dequeued = await queue.dequeue()
    assert dequeued.id == created_run.id
    assert dequeued.status == ScraperJobStatus.STARTED
    assert await queue.dequeue() is None
    await queue.ping_scraper_job(dequeued.scraper.id, dequeued.id)
    dequeued.status = ScraperJobStatus.SUCCEEDED
    dequeued.finished_at = datetime.utcnow()
    finished = await jobs_storage.update_scraper_job(dequeued)
    with pytest.raises(ScraperJobPingFinishedError):
        await queue.ping_scraper_job(finished.scraper.id, finished.id)
    assert await queue.dequeue() is None


@pytest.mark.asyncio
async def test_scraper_priority_queue_dequeue_order(
    scrapers_storage: ScrapersStorage, jobs_storage: ScrapersStorage
):
    queue = Queue(scrapers_storage, jobs_storage)
    run_utmost_priority_dequeued_1st = await scrapers_storage.create_scraper(
        _get_scraper("run_utmost_priority_dequeued_1st")
    )
    run_high_priority_dequeued_2nd = await scrapers_storage.create_scraper(
        _get_scraper("run_high_priority_dequeued_2nd")
    )
    run_high_priority_dequeued_3rd = await scrapers_storage.create_scraper(
        _get_scraper("run_high_priority_dequeued_3rd")
    )
    run_normal_priority_dequeued_4th = await scrapers_storage.create_scraper(
        _get_scraper("run_normal_priority_dequeued_4th")
    )
    for scraper, priority in [
        (run_normal_priority_dequeued_4th, ScraperJobPriority.NORMAL),
        (run_high_priority_dequeued_2nd, ScraperJobPriority.HIGH),
        (run_high_priority_dequeued_3rd, ScraperJobPriority.HIGH),
        (run_utmost_priority_dequeued_1st, ScraperJobPriority.UTMOST),
    ]:
        await queue.enqueue(scraper.id, priority)
    expected_dequeud_scrapers = [
        "run_utmost_priority_dequeued_1st",
        "run_high_priority_dequeued_2nd",
        "run_high_priority_dequeued_3rd",
        "run_normal_priority_dequeued_4th",
        None,
    ]
    dequeued = [await queue.dequeue() for _ in range(len(expected_dequeud_scrapers))]
    dequeued = [item.scraper.name if item is not None else None for item in dequeued]
    assert dequeued == expected_dequeud_scrapers
