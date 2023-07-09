import asyncio
from collections import defaultdict
from itertools import count
from typing import Iterator

from typing_extensions import override

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.queue.model import QueueStorageABC, Task, TaskNotFoundError

SCORE_PRIORITY_BIT_OFFSET = 32


class InMemoryQueueStorage(QueueStorageABC):
    """In memory queue storage (should only be used for development purposes)"""

    def __init__(self) -> None:
        """
        Args:
            redis (Redis): Async redis client
        """
        self._id_generator: Iterator[int] = count(1)
        self._queue = asyncio.PriorityQueue()
        self._tasks: dict[str, set[int]] = defaultdict(set)
        self._task_instances: dict[int, Task] = {}
        self._lock = asyncio.Lock()

    async def _generate_id(self) -> int:
        return next(self._id_generator)

    def _get_task_score(self, task: Task) -> int:
        return (task.priority.value << SCORE_PRIORITY_BIT_OFFSET) + task.id

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_tasks(self) -> list[Task]:
        return sorted(self._task_instances.values(), key=lambda x: x.id)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_task_instances(self, task_name: str) -> list[Task]:
        return sorted(
            [
                self._task_instances[task_id]
                for task_id in self._tasks.get(task_name, [])
            ],
            key=lambda x: x.id,
            reverse=True,
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_task_instance(self, id: int) -> Task:
        if id not in self._task_instances:
            raise TaskNotFoundError()
        return self._task_instances[id]

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def enqueue_task(self, task: Task) -> Task:
        task.id = await self._generate_id()
        self._tasks[task.task_name].add(task.id)
        self._task_instances[task.id] = task
        await self._queue.put((self._get_task_score(task), task.id))
        return task

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def update_task(self, task: Task) -> Task:
        if task.id not in self._task_instances:
            raise TaskNotFoundError()
        self._task_instances[task.id] = task
        return task

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def dequeue_task(self) -> Task | None:
        try:
            _, task_id = self._queue.get_nowait()
            return await self.get_task_instance(task_id)
        except asyncio.QueueEmpty:
            return None

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def delete_old_tasks(self, keep_last: int = 50) -> None:
        for task_name, task_ids in self._tasks.items():
            for task_id in sorted(task_ids, reverse=True)[keep_last:]:
                self._task_instances.pop(task_id)
                self._tasks[task_name].remove(task_id)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_queue_len(self) -> int:
        return self._queue.qsize()
