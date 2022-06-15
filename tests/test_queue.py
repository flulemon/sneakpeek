import pytest

from sneakpeek.lib.models import UNSET_ID, Scraper, ScraperRunPriority, ScraperSchedule
from sneakpeek.lib.queue import Queue, ScraperHasActiveRunError
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
        config="config_{name}",
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
