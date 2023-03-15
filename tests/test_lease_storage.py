import asyncio
from datetime import timedelta

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.lib.storage.base import LeaseStorage
from sneakpeek.lib.storage.in_memory_storage import InMemoryLeaseStorage
from sneakpeek.lib.storage.redis_storage import RedisLeaseStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> LeaseStorage:
    return InMemoryLeaseStorage()


@pytest.fixture
def redis_storage() -> LeaseStorage:
    return RedisLeaseStorage(FakeRedis())


storages = [
    pytest.lazy_fixture(in_memory_storage.__name__),
    pytest.lazy_fixture(redis_storage.__name__),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_lease(storage: LeaseStorage):
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
