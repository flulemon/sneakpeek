from datetime import datetime

import pytest

from sneakpeek.config import ScraperConfig
from sneakpeek.lib.errors import (
    ScraperHasActiveRunError,
    ScraperRunPingFinishedError,
    ScraperRunPingNotStartedError,
)
from sneakpeek.lib.models import (
    UNSET_ID,
    Scraper,
    ScraperRunPriority,
    ScraperRunStatus,
    ScraperSchedule,
)
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.base import Storage
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def storage() -> Storage:
    return InMemoryStorage()


@pytest.fixture
def queue(storage: Storage) -> Queue:
    return Queue(storage)


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
async def test_enqueue_dequeue(queue: Queue, storage: Storage):
    scraper = await storage.create_scraper(_get_scraper("test_enqueue_dequeue"))
    enqueued = await queue.enqueue(scraper.id, ScraperRunPriority.NORMAL)
    dequeued = await queue.dequeue()
    assert enqueued == dequeued


@pytest.mark.asyncio
async def test_double_enqueue_forbidden(queue: Queue, storage: Storage):
    scraper = await storage.create_scraper(
        _get_scraper("test_double_enqueue_forbidden")
    )
    await queue.enqueue(scraper.id, ScraperRunPriority.NORMAL)
    with pytest.raises(ScraperHasActiveRunError):
        await queue.enqueue(scraper.id, ScraperRunPriority.NORMAL)


@pytest.mark.asyncio
async def test_enqueue_count_equals_dequeue_count(queue: Queue, storage: Storage):
    expected = []
    tasks_to_enqueue = 10
    for i in range(tasks_to_enqueue):
        scraper = await storage.create_scraper(_get_scraper(f"test_enqueue_order_{i}"))
        enqueued = await queue.enqueue(scraper.id, ScraperRunPriority.NORMAL)
        expected.append(enqueued.id)

    dequeued = []
    for i in range(tasks_to_enqueue):
        dequeued.append((await queue.dequeue()).id)
    assert dequeued == expected
    await queue.dequeue() is None


@pytest.mark.asyncio
async def test_scraper_queue(queue: Queue, storage: Storage):
    created_scraper = await storage.create_scraper(_get_scraper("test_scraper_queue"))
    created_run = await queue.enqueue(created_scraper.id, ScraperRunPriority.UTMOST)
    assert created_run.id >= 0, "Expected scraper run ID to be positive or zero"
    assert created_run.scraper == created_scraper
    assert created_run.status == ScraperRunStatus.PENDING
    actual_run = await storage.get_scraper_runs(created_scraper.id)
    assert actual_run == [created_run]
    with pytest.raises(ScraperRunPingNotStartedError):
        await queue.ping_scraper_run(created_scraper.id, created_run.id)
    dequeued = await queue.dequeue()
    assert dequeued.id == created_run.id
    assert dequeued.status == ScraperRunStatus.STARTED
    assert await queue.dequeue() is None
    await queue.ping_scraper_run(dequeued.scraper.id, dequeued.id)
    dequeued.status = ScraperRunStatus.SUCCEEDED
    dequeued.finished_at = datetime.utcnow()
    finished = await storage.update_scraper_run(dequeued)
    with pytest.raises(ScraperRunPingFinishedError):
        await queue.ping_scraper_run(finished.scraper.id, finished.id)
    assert await queue.dequeue() is None


@pytest.mark.asyncio
async def test_scraper_priority_queue_dequeue_order(queue: Queue, storage: Storage):
    run_utmost_priority_dequeued_1st = await storage.create_scraper(
        _get_scraper("run_utmost_priority_dequeued_1st")
    )
    run_high_priority_dequeued_2nd = await storage.create_scraper(
        _get_scraper("run_high_priority_dequeued_2nd")
    )
    run_high_priority_dequeued_3rd = await storage.create_scraper(
        _get_scraper("run_high_priority_dequeued_3rd")
    )
    run_normal_priority_dequeued_4th = await storage.create_scraper(
        _get_scraper("run_normal_priority_dequeued_4th")
    )
    for scraper, priority in [
        (run_normal_priority_dequeued_4th, ScraperRunPriority.NORMAL),
        (run_high_priority_dequeued_2nd, ScraperRunPriority.HIGH),
        (run_high_priority_dequeued_3rd, ScraperRunPriority.HIGH),
        (run_utmost_priority_dequeued_1st, ScraperRunPriority.UTMOST),
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
