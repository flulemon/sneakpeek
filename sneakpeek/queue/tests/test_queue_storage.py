from datetime import datetime, timedelta

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.queue.in_memory_storage import InMemoryQueueStorage
from sneakpeek.queue.model import QueueStorageABC, Task, TaskPriority, TaskStatus
from sneakpeek.queue.redis_storage import RedisQueueStorage


@pytest.fixture
def in_memory_storage() -> QueueStorageABC:
    yield InMemoryQueueStorage()


@pytest.fixture
def redis_storage() -> QueueStorageABC:
    yield RedisQueueStorage(FakeRedis())


@pytest.fixture(
    params=[
        pytest.lazy_fixture(in_memory_storage.__name__),
        pytest.lazy_fixture(redis_storage.__name__),
    ]
)
def storage(request) -> QueueStorageABC:
    yield request.param


@pytest.mark.asyncio
async def test_storage_crud(storage: QueueStorageABC) -> None:
    task = Task(
        id=0,
        task_name=f"{test_storage_crud.__name__}:task_name",
        task_handler=f"{test_storage_crud.__name__}:task_handler",
        status=TaskStatus.PENDING,
        created_at=datetime.utcnow(),
        priority=TaskPriority.NORMAL,
        payload=f"{test_storage_crud.__name__}:payload",
        timeout=timedelta(seconds=1),
    )
    # Create task
    enqueued = await storage.enqueue_task(task)
    assert enqueued.id > 0
    assert enqueued.task_name == task.task_name

    # Get task
    all_tasks = await storage.get_tasks()
    assert all_tasks == [enqueued]
    task_name_instances = await storage.get_task_instances(task.task_name)
    assert task_name_instances == [enqueued]
    actual_task = await storage.get_task_instance(enqueued.id)
    assert enqueued == actual_task

    # Update task
    enqueued.last_active_at = datetime(year=1, month=10, day=1)
    updated = await storage.update_task(enqueued)
    assert updated.id == enqueued.id
    assert enqueued.last_active_at == updated.last_active_at

    # Queue len
    assert await storage.get_queue_len() == 1

    # Dequeue
    dequeued = await storage.dequeue_task()
    assert dequeued.id == enqueued.id


@pytest.mark.asyncio
async def test_delete_old_items(storage: QueueStorageABC) -> None:
    keep_last = 2
    total_tasks = 4
    tasks = [
        Task(
            id=0,
            task_name=f"{test_delete_old_items.__name__}:task_name",
            task_handler=f"{test_delete_old_items.__name__}:task_handler",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            priority=TaskPriority.NORMAL,
            payload=f"{test_delete_old_items.__name__}:payload:{i}",
            timeout=timedelta(seconds=1),
        )
        for i in range(total_tasks)
    ]
    enqueued_tasks = [await storage.enqueue_task(task) for task in tasks]

    await storage.delete_old_tasks(keep_last)
    actual_left_tasks = await storage.get_tasks()
    assert sorted(actual_left_tasks, key=lambda x: x.id) == sorted(
        enqueued_tasks[keep_last:], key=lambda x: x.id
    )
