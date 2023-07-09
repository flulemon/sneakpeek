import asyncio
from datetime import timedelta

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.scheduler.in_memory_lease_storage import InMemoryLeaseStorage
from sneakpeek.scheduler.model import LeaseStorageABC
from sneakpeek.scheduler.redis_lease_storage import RedisLeaseStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> LeaseStorageABC:
    return InMemoryLeaseStorage()


@pytest.fixture
def redis_storage() -> LeaseStorageABC:
    return RedisLeaseStorage(FakeRedis())


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def storage(request) -> LeaseStorageABC:
    yield request.param


@pytest.mark.asyncio
async def test_lease(storage: LeaseStorageABC):
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
