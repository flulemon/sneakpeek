import asyncio

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.queue.in_memory_storage import InMemoryQueueStorage
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueABC,
    QueueStorageABC,
    TaskHasActiveRunError,
    TaskPriority,
)
from sneakpeek.queue.queue import Queue
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
def queue_storage(request) -> QueueStorageABC:
    yield request.param


@pytest.fixture
def queue(queue_storage: QueueStorageABC) -> QueueABC:
    yield Queue(queue_storage)


@pytest.mark.asyncio
async def test_enqueue_dequeue(queue: Queue):
    request = EnqueueTaskRequest(
        task_name=test_enqueue_dequeue.__name__ + ":name",
        task_handler=test_enqueue_dequeue.__name__ + ":type",
        priority=TaskPriority.HIGH,
        payload=test_enqueue_dequeue.__name__ + ":payload",
    )
    enqueued = await queue.enqueue(request)
    assert enqueued.id is not None
    assert enqueued.task_name == request.task_name
    assert enqueued.task_handler == request.task_handler
    assert enqueued.priority == request.priority
    assert enqueued.payload == request.payload
    dequeued = await queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == enqueued.id
    assert dequeued.task_name == request.task_name
    assert dequeued.task_handler == request.task_handler
    assert dequeued.priority == request.priority
    assert dequeued.payload == request.payload


@pytest.mark.asyncio
async def test_double_enqueue_forbidden(queue: Queue):
    request = EnqueueTaskRequest(
        task_name=test_double_enqueue_forbidden.__name__ + ":name",
        task_handler=test_double_enqueue_forbidden.__name__ + ":type",
        priority=TaskPriority.HIGH,
        payload=test_double_enqueue_forbidden.__name__ + ":payload",
    )
    enqueued = await queue.enqueue(request)
    assert enqueued.id is not None
    assert enqueued.task_name == request.task_name
    with pytest.raises(TaskHasActiveRunError):
        await queue.enqueue(request)


@pytest.mark.asyncio
async def test_enqueue_count_equals_dequeue_count(queue: Queue):
    requests = [
        EnqueueTaskRequest(
            task_name=f"{test_enqueue_count_equals_dequeue_count.__name__}:name:{i}",
            task_handler=f"{test_enqueue_count_equals_dequeue_count.__name__}:type:{i}",
            priority=TaskPriority.HIGH,
            payload=f"{test_enqueue_count_equals_dequeue_count.__name__}:payload:{i}",
        )
        for i in range(100)
    ]
    enqueued_tasks = await asyncio.gather(
        *{queue.enqueue(request) for request in requests}
    )
    assert len(enqueued_tasks) == len(requests)
    assert {request.task_name for request in requests} == {
        task.task_name for task in enqueued_tasks
    }

    dequeued = []
    while task := await queue.dequeue():
        dequeued.append(task)
    assert len(dequeued) == len(requests)
    assert {request.task_name for request in requests} == {
        task.task_name for task in dequeued
    }


@pytest.mark.asyncio
async def test_scraper_priority_queue_dequeue_order(queue: Queue):
    def get_enqueue_request(priority: TaskPriority):
        return EnqueueTaskRequest(
            task_name=f"{test_scraper_priority_queue_dequeue_order.__name__}:name:{priority}",
            task_handler=f"{test_scraper_priority_queue_dequeue_order.__name__}:type:{priority}",
            payload=f"{test_scraper_priority_queue_dequeue_order.__name__}:payload:{priority}",
            priority=priority,
        )

    requests = [
        get_enqueue_request(TaskPriority.NORMAL),
        get_enqueue_request(TaskPriority.HIGH),
        get_enqueue_request(TaskPriority.UTMOST),
    ]
    for request in requests:
        await queue.enqueue(request)

    dequeued = []
    while task := await queue.dequeue():
        dequeued.append(task.priority)
    assert dequeued == [TaskPriority.UTMOST, TaskPriority.HIGH, TaskPriority.NORMAL]
