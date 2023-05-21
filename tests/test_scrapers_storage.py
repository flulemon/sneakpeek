import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.errors import ScraperNotFoundError
from sneakpeek.models import UNSET_ID, Scraper, ScraperSchedule
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.storage.base import ScrapersStorage
from sneakpeek.storage.in_memory_storage import InMemoryScrapersStorage
from sneakpeek.storage.redis_storage import RedisScrapersStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> ScrapersStorage:
    return InMemoryScrapersStorage()


@pytest.fixture
def redis_storage() -> ScrapersStorage:
    return RedisScrapersStorage(FakeRedis())


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
        config=ScraperConfig(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_read_after_write(storage: ScrapersStorage):
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
async def test_get_scrapers(storage: ScrapersStorage):
    expected = [_get_scraper(f"test_get_scrapers_{i}", i) for i in range(1, 10)]
    for item in expected:
        await storage.create_scraper(item)

    actual = await storage.get_scrapers()
    assert actual == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_search_scrapers(storage: ScrapersStorage):
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
async def test_read_non_existent_scraper_throws(storage: ScrapersStorage):
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_maybe_read_non_existent_scraper_returns_none(storage: ScrapersStorage):
    actual = await storage.maybe_get_scraper(NON_EXISTENT_SCRAPER_ID)
    assert actual is None


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_update_non_existent_scraper_throws(storage: ScrapersStorage):
    with pytest.raises(ScraperNotFoundError):
        await storage.update_scraper(
            _get_scraper(
                "test_update_non_existent_scraper_throws",
                NON_EXISTENT_SCRAPER_ID,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_delete_non_existent_scraper_throws(storage: ScrapersStorage):
    with pytest.raises(ScraperNotFoundError):
        await storage.delete_scraper(NON_EXISTENT_SCRAPER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", storages)
async def test_delete_scraper(storage: ScrapersStorage):
    created = await storage.create_scraper(_get_scraper("test_delete_scraper"))
    actual = await storage.get_scraper(created.id)
    assert created == actual
    deleted = await storage.delete_scraper(actual.id)
    assert deleted == actual
    with pytest.raises(ScraperNotFoundError):
        await storage.get_scraper(actual.id)
