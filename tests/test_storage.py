import asyncio
from datetime import datetime, timedelta

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.lib.models import (
    UNSET_ID,
    Scraper,
    ScraperRun,
    ScraperRunPriority,
    ScraperRunStatus,
    ScraperSchedule,
)
from sneakpeek.lib.storage.base import ScraperNotFoundError, Storage
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
from sneakpeek.lib.storage.redis_storage import RedisStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> Storage:
    return InMemoryStorage()


@pytest.fixture
def redis_storage() -> Storage:
    return RedisStorage(FakeRedis())


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
        config=f"config_{name}",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
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
@pytest.mark.parametrize("storage", storages)
async def test_get_scrapers(storage: Storage):
    expected = [_get_scraper(f"test_get_scrapers_{i}", i) for i in range(10)]
    for item in expected:
        await storage.create_scraper(item)

    actual = await storage.get_scrapers()
    assert actual == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
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
@pytest.mark.parametrize("storage", storages)
async def test_read_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_maybe_read_non_existent_scraper_returns_none(storage: Storage):
    actual = await storage.maybe_get_scraper(NON_EXISTENT_SCRAPER_ID)
    assert actual is None


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_update_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.update_scraper(
            _get_scraper(
                "test_update_non_existent_scraper_throws",
                NON_EXISTENT_SCRAPER_ID,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_delete_non_existent_scraper_throws(storage: Storage):
    with pytest.raises(ScraperNotFoundError):
        await storage.delete_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_delete_scraper(storage: Storage):
    created = await storage.create_scraper(_get_scraper("test_delete_scraper"))
    actual = await storage.get_scraper(created.id)
    assert created == actual
    deleted = await storage.delete_scraper(actual.id)
    assert deleted == actual
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(actual.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
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
@pytest.mark.parametrize("storage", storages)
async def test_lease(storage: Storage):
    lease_name_1 = "test_lease_1"
    lease_name_2 = "test_lease_2"
    owner_1 = "owner_id_1"
    owner_2 = "owner_id_2"
    owner_1_acquire_until = timedelta(seconds=1)
    owner_2_acquire_until = timedelta(seconds=5)

    # initial acquire
    assert (
        await storage.maybe_acquire_lease(lease_name_1, owner_1, owner_1_acquire_until)
        is not None
    )
    # another lease can be acquired
    assert (
        await storage.maybe_acquire_lease(lease_name_2, owner_2, owner_2_acquire_until)
        is not None
    )
    # lock is acquired so no one can acquire
    assert (
        await storage.maybe_acquire_lease(lease_name_1, owner_2, owner_2_acquire_until)
        is None
    )
    # owner can re-acquire
    assert (
        await storage.maybe_acquire_lease(lease_name_1, owner_1, owner_1_acquire_until)
        is not None
    )

    # lock expires and can be acuired
    await asyncio.sleep(1)
    assert (
        await storage.maybe_acquire_lease(lease_name_1, owner_2, owner_2_acquire_until)
        is not None
    )
