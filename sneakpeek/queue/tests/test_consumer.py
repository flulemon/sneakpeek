import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis

from sneakpeek.queue.consumer import Consumer
from sneakpeek.queue.in_memory_storage import InMemoryQueueStorage
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueABC,
    QueueStorageABC,
    Task,
    TaskHandlerABC,
    TaskPriority,
    TaskStatus,
)
from sneakpeek.queue.queue import Queue
from sneakpeek.queue.redis_storage import RedisQueueStorage

TEST_HANDLER_NAME = "test_handler"
PING_DELAY = timedelta(milliseconds=1)


class TestTaskHandler(TaskHandlerABC):
    def __init__(self) -> None:
        self.process_mock = AsyncMock()

    def name(self):
        return TEST_HANDLER_NAME

    async def process(self, task: Task) -> str:
        await self.process_mock(task.id)
        return task.task_name


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


@pytest.fixture
def handler() -> TaskHandlerABC:
    yield TestTaskHandler()


@pytest.fixture
def consumer(queue: QueueABC, handler: TaskHandlerABC) -> Consumer:
    yield Consumer(queue, [handler], ping_delay=PING_DELAY)


async def _wait_task_in_finished_state(queue: QueueABC, task: Task, timeout: timedelta):
    async def wait(task: Task):
        while True:
            task = await queue.storage.get_task_instance(task.id)
            if task.status not in (TaskStatus.STARTED, TaskStatus.PENDING):
                return
            await asyncio.sleep(PING_DELAY.total_seconds())

    await asyncio.wait_for(wait(task), timeout=timeout.total_seconds())


@pytest.mark.asyncio
async def test_task_dequeues_and_succeeds(
    consumer: Consumer,
    queue: Queue,
    handler: TaskHandlerABC,
):
    request = EnqueueTaskRequest(
        task_name="test_task",
        task_handler=TEST_HANDLER_NAME,
        priority=TaskPriority.NORMAL,
        payload="payload",
    )
    task = await queue.enqueue(request)
    assert await consumer.consume()
    await _wait_task_in_finished_state(queue, task, timedelta(seconds=2))
    assert await queue.get_queue_len() == 0
    task = await queue.storage.get_task_instance(task.id)
    assert task.status == TaskStatus.SUCCEEDED
    assert task.result == task.task_name
    assert handler.process_mock.awaited_once_with(task.id)


@pytest.mark.asyncio
async def test_dequeues_and_fails(
    consumer: Consumer,
    queue: Queue,
    handler: TaskHandlerABC,
):
    handler.process_mock.side_effect = Exception()
    request = EnqueueTaskRequest(
        task_name="test_task",
        task_handler=TEST_HANDLER_NAME,
        priority=TaskPriority.NORMAL,
        payload="payload",
    )
    task = await queue.enqueue(request)
    assert await consumer.consume()
    await _wait_task_in_finished_state(queue, task, timedelta(seconds=2))
    assert await queue.get_queue_len() == 0
    task = await queue.storage.get_task_instance(task.id)
    assert task.status == TaskStatus.FAILED
    assert handler.process_mock.awaited_once_with(task.id)


@pytest.mark.asyncio
async def test_dequeues_and_times_out(
    consumer: Consumer,
    queue: Queue,
    handler: TaskHandlerABC,
):
    handler.process_mock.side_effect = asyncio.sleep(10)
    request = EnqueueTaskRequest(
        task_name="test_task",
        task_handler=TEST_HANDLER_NAME,
        priority=TaskPriority.NORMAL,
        payload="payload",
        timeout=timedelta(milliseconds=10),
    )
    task = await queue.enqueue(request)
    assert await consumer.consume()
    await _wait_task_in_finished_state(queue, task, timedelta(seconds=2))
    assert await queue.get_queue_len() == 0
    task = await queue.storage.get_task_instance(task.id)
    assert task.status == TaskStatus.FAILED
    assert handler.process_mock.awaited_once_with(task.id)
