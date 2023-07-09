from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.scheduler.model import TaskSchedule
from sneakpeek.scraper.in_memory_storage import InMemoryScraperStorage
from sneakpeek.scraper.model import (
    CreateScraperRequest,
    Scraper,
    ScraperConfig,
    ScraperNotFoundError,
    ScraperStorageABC,
)
from sneakpeek.scraper.redis_storage import RedisScraperStorage


@pytest.fixture
def in_memory_storage() -> ScraperStorageABC:
    yield InMemoryScraperStorage()


@pytest.fixture
def redis_storage() -> ScraperStorageABC:
    yield RedisScraperStorage(FakeRedis())


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def storage(request) -> ScraperStorageABC:
    yield request.param


def _get_create_scraper_request(name: str) -> CreateScraperRequest:
    return CreateScraperRequest(
        name=name,
        schedule=TaskSchedule.CRONTAB,
        schedule_crontab=f"schedule_{name}",
        handler=f"handler_{name}",
        config=ScraperConfig(),
    )


@pytest.mark.asyncio
async def test_read_after_write(storage: ScraperStorageABC):
    expected = _get_create_scraper_request("test_read_after_write")
    created = await storage.create_scraper(expected)
    assert created.id is not None, "Expected storage to create a scraper"
    assert created.name == expected.name
    assert created.schedule == expected.schedule
    assert created.schedule_crontab == expected.schedule_crontab
    assert created.handler == expected.handler
    assert created.config == expected.config
    actual = await storage.get_scraper(created.id)
    assert actual == created
    created.name = f"{created.name}_updated"
    actual = await storage.update_scraper(created)
    actual = await storage.get_scraper(created.id)
    assert actual == created


@pytest.mark.asyncio
async def test_get_scrapers(storage: ScraperStorageABC):
    expected = [
        _get_create_scraper_request(f"test_get_scrapers_{i}") for i in range(1, 10)
    ]
    for item in expected:
        await storage.create_scraper(item)

    actual = await storage.get_scrapers()
    assert {item.name for item in actual} == {item.name for item in expected}


@pytest.mark.asyncio
async def test_read_non_existent_scraper_throws(storage: ScraperStorageABC):
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(uuid4())


@pytest.mark.asyncio
async def test_update_non_existent_scraper_throws(storage: ScraperStorageABC):
    with pytest.raises(ScraperNotFoundError):
        await storage.update_scraper(
            Scraper(
                id=str(uuid4()),
                name="test_update_non_existent_scraper_throws",
                schedule=TaskSchedule.CRONTAB,
                schedule_crontab="schedule_test_update_non_existent_scraper_throws",
                handler="handler_test_update_non_existent_scraper_throws",
                config=ScraperConfig(),
            )
        )


@pytest.mark.asyncio
async def test_delete_non_existent_scraper_throws(storage: ScraperStorageABC):
    with pytest.raises(ScraperNotFoundError):
        await storage.delete_scraper(uuid4())


@pytest.mark.asyncio
async def test_delete_scraper(storage: ScraperStorageABC):
    created = await storage.create_scraper(
        _get_create_scraper_request("test_delete_scraper")
    )
    actual = await storage.get_scraper(created.id)
    assert created == actual
    deleted = await storage.delete_scraper(actual.id)
    assert deleted == actual
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(actual.id)
