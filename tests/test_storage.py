import pytest
from pytest_lazyfixture import lazy_fixture

from sneakpeek.lib.models import Scraper, ScraperSchedule
from sneakpeek.lib.storage.base import ScraperNotFoundError, Storage
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage

NON_EXISTENT_SCRAPER_ID = 10001


@pytest.fixture
def in_memory_storage() -> Storage:
    return InMemoryStorage()


def _get_scraper(name: str, id: int = -1) -> Scraper:
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
