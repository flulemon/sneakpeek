

import pytest
from pytest_lazyfixture import lazy_fixture

from sneakpeek.lib.models import Scraper, ScraperSchedule
from sneakpeek.lib.storage.base import Storage
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage


@pytest.fixture
def in_memory_storage() -> Storage:
    return InMemoryStorage()


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [lazy_fixture('in_memory_storage')])
async def test_read_after_write(storage: Storage):
    expected = Scraper(
        id=0,
        name="test_read_after_write",
        schedule=ScraperSchedule.CRONTAB,
        schedule_crontab="schedule_crontab",
        handler="handler",
        config="config",
    )
    created = await storage.create_scraper(expected)
    assert created.id is not None, "Expected storage to create a scraper"
    assert created.id >= 0, "Expected scraper ID to be positive or zero"
    assert created == expected
    actual = await storage.get_scraper(created.id)
    assert actual == expected
