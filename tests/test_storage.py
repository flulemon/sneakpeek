import asyncio
from datetime import datetime, timedelta

import pytest
from pytest_lazyfixture import lazy_fixture

from sneakpeek.lib.models import (
    UNSET_ID,
    Scraper,
    ScraperRun,
    ScraperRunPriority,
    ScraperRunStatus,
    ScraperSchedule,
)
from sneakpeek.lib.storage.base import (
    ScraperNotFoundError,
    ScraperRunPingFinishedError,
    ScraperRunPingNotStartedError,
    Storage,
)
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> Storage:
    return InMemoryStorage()


def _get_scraper(name: str, id: int = UNSET_ID) -> Scraper:
    return Scraper(
        id=id,
        name=name,
        schedule=ScraperSchedule.CRONTAB,
        schedule_crontab=f"schedule_{name}",
        handler="handler_{name}",
        config="config_{name}",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_read_after_write(storage: Storage):
    expected = _get_scraper("test_read_after_write")
    created = await storage.create_scraper(expected)
    assert created.id is not None, "Expected storage to create a scraper"
    assert created.id >= 0, "Expected scraper ID to be positive or zero"
    assert created == expected
    actual = await storage.get_scraper(created.id)
    assert actual == expected
    created.name = f"{created.name}_updated"
    actual = await storage.update_scraper(created)
    actual = await storage.get_scraper(created.id)
    assert actual == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_get_scrapers(storage: Storage):
    expected = [_get_scraper(f"test_get_scrapers_{i}", i) for i in range(10)]
    for item in expected:
        await storage.create_scraper(item)

    actual = await storage.get_scrapers()
    assert actual == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_search_scrapers(storage: Storage):
    name_filter = "test_that_must_be_found"
    last_id = 50
    max_items = 5
    must_be_found = [
        _get_scraper(
            f"test_search_scrapers_{last_id + i + 2}_{name_filter}",
            id=last_id + i + 2,
        )
        for i in range(max_items)
    ]
    must_not_be_found = [
        _get_scraper(
            "test_search_scrapers_name_doesnt_match",
            id=last_id + 1,
        ),
        _get_scraper(
            "test_search_scrapers_name_id_too_small_{name_filter}",
            id=last_id,
        ),
        _get_scraper(
            "test_search_scrapers_name_id_too_big_{name_filter}",
            id=last_id + max_items + 10,
        ),
    ]
    for item in must_be_found + must_not_be_found:
        await storage.create_scraper(item)

    actual = await storage.search_scrapers(name_filter, max_items, last_id)
    for item in actual:
        assert any(expected for expected in must_be_found if expected.name == item.name)
        assert not any(
            expected for expected in must_not_be_found if expected.name == item.name
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_read_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_maybe_read_non_existent_scraper_returns_none(storage: Storage):
    actual = await storage.maybe_get_scraper(NON_EXISTENT_SCRAPER_ID)
    assert actual is None


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_update_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.update_scraper(
            _get_scraper(
                "test_update_non_existent_scraper_throws",
                NON_EXISTENT_SCRAPER_ID,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_delete_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.delete_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_delete_scraper(storage: Storage):
    created = await storage.create_scraper(_get_scraper("test_delete_scraper"))
    actual = await storage.get_scraper(created.id)
    assert created == actual
    deleted = await storage.delete_scraper(actual.id)
    assert deleted == actual
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(actual.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_scraper_queue(storage: Storage):
    created_scraper = await storage.create_scraper(_get_scraper("test_scraper_queue"))
    created_run = await storage.add_scraper_run(
        ScraperRun(
            id=UNSET_ID,
            scraper=created_scraper,
            status=ScraperRunStatus.PENDING,
            priority=ScraperRunPriority.UTMOST,
            created_at=datetime(year=2000, month=12, day=31),
        )
    )
    assert created_run.id >= 0, "Expected scraper run ID to be positive or zero"
    assert created_run.scraper == created_scraper
    assert created_run.status == ScraperRunStatus.PENDING
    actual_run = await storage.get_scraper_runs(created_scraper.id)
    assert actual_run == [created_run]
    has_unfinished_scraper_runs = await storage.has_unfinished_scraper_runs(
        created_scraper.id
    )
    assert has_unfinished_scraper_runs is True
    with pytest.raises(ScraperRunPingNotStartedError):
        await storage.ping_scraper_run(created_scraper.id, created_run.id)
    dequeued = await storage.dequeue_scraper_run()
    assert dequeued.id == created_run.id
    assert dequeued.status == ScraperRunStatus.STARTED
    assert await storage.dequeue_scraper_run() is None
    await storage.ping_scraper_run(dequeued.scraper.id, dequeued.id)
    dequeued.status = ScraperRunStatus.SUCCEEDED
    dequeued.finished_at = datetime.utcnow()
    finished = await storage.update_scraper_run(dequeued)
    with pytest.raises(ScraperRunPingFinishedError):
        await storage.ping_scraper_run(finished.scraper.id, finished.id)
    assert await storage.dequeue_scraper_run() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_scraper_priority_queue_dequeue_order(storage: Storage):
    created_scraper = await storage.create_scraper(_get_scraper("test_scraper_queue"))
    NORMAL_PRIORITY_DEQUEUED_4 = 1
    HIGH_PRIORITY_LOWER_ID_DEQUEUED_3 = 2
    HIGH_PRIORITY_HIGHER_ID_DEQUEUED_2 = 3
    UTMOST_PRIORITY_DEQUEUED_1 = 4
    expected_dequeued_ids = [
        UTMOST_PRIORITY_DEQUEUED_1,
        HIGH_PRIORITY_HIGHER_ID_DEQUEUED_2,
        HIGH_PRIORITY_LOWER_ID_DEQUEUED_3,
        NORMAL_PRIORITY_DEQUEUED_4,
        None,
    ]
    runs = [
        ScraperRun(
            id=NORMAL_PRIORITY_DEQUEUED_4,
            scraper=created_scraper,
            status=ScraperRunStatus.PENDING,
            priority=ScraperRunPriority.NORMAL,
            created_at=datetime(year=2000, month=12, day=31),
        ),
        ScraperRun(
            id=HIGH_PRIORITY_LOWER_ID_DEQUEUED_3,
            scraper=created_scraper,
            status=ScraperRunStatus.PENDING,
            priority=ScraperRunPriority.HIGH,
            created_at=datetime(year=2000, month=12, day=31),
        ),
        ScraperRun(
            id=HIGH_PRIORITY_HIGHER_ID_DEQUEUED_2,
            scraper=created_scraper,
            status=ScraperRunStatus.PENDING,
            priority=ScraperRunPriority.HIGH,
            created_at=datetime(year=2000, month=12, day=31),
        ),
        ScraperRun(
            id=UTMOST_PRIORITY_DEQUEUED_1,
            scraper=created_scraper,
            status=ScraperRunStatus.PENDING,
            priority=ScraperRunPriority.UTMOST,
            created_at=datetime(year=2000, month=12, day=31),
        ),
    ]
    for run in runs:
        await storage.add_scraper_run(run)
    dequeued = [
        await storage.dequeue_scraper_run() for _ in range(len(expected_dequeued_ids))
    ]
    dequeued = [item.id if item is not None else None for item in dequeued]
    assert dequeued == expected_dequeued_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_delete_old_scraper_runs(storage: Storage):
    scraper = await storage.create_scraper(_get_scraper("test_scraper_queue"))
    to_create = 10
    to_keep = 5
    start_id = 0
    for i in range(to_create):
        await storage.add_scraper_run(
            ScraperRun(
                id=start_id + i,
                scraper=scraper,
                status=ScraperRunStatus.PENDING,
                priority=ScraperRunPriority.NORMAL,
                created_at=datetime(year=2000, month=12, day=31),
            )
        )
    await storage.delete_old_scraper_runs(to_keep)
    kept_runs = await storage.get_scraper_runs(scraper.id)
    assert len(kept_runs) == to_keep
    for run in kept_runs:
        assert run.id > to_create - to_keep - 1


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture("in_memory_storage")])
async def test_lease(storage: Storage):
    lease_name = "test_lease"
    owner_1 = "owner_id_1"
    owner_2 = "owner_id_2"
    now = datetime.utcnow()
    owner_1_acquire_until = now + timedelta(seconds=1)
    owner_2_acquire_until = now + timedelta(seconds=5)

    # initial acquire
    assert (
        await storage.maybe_acquire_lease(lease_name, owner_1, owner_1_acquire_until)
        is not None
    )
    # lock is acquired so no one can acquire
    assert (
        await storage.maybe_acquire_lease(lease_name, owner_2, owner_2_acquire_until)
        is None
    )
    # owner can re-acquire
    assert (
        await storage.maybe_acquire_lease(lease_name, owner_1, owner_1_acquire_until)
        is not None
    )

    # lock expires and can be acuired
    await asyncio.sleep(1)
    assert (
        await storage.maybe_acquire_lease(lease_name, owner_2, owner_2_acquire_until)
        is not None
    )
