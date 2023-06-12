from datetime import timedelta

from redis.asyncio import Redis
from typing_extensions import override

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.queue.model import QueueStorageABC, Task, TaskNotFoundError

DEFAULT_TASK_TTL = timedelta(days=7)
SCORE_PRIORITY_BIT_OFFSET = 32


class RedisQueueStorage(QueueStorageABC):
    """
    Redis queue storage. Queue has two components: priority queue
    implemented by sorted set (ZADD and ZPOPMIN) and key (task name)
    values (set of task instances) set
    """

    def __init__(self, redis: Redis, task_ttl: timedelta = DEFAULT_TASK_TTL) -> None:
        """

        Args:
            redis (Redis): Async redis client
            task_ttl (timedelta): TTL of the task record in the redis. Defaults to 7 days.
        """
        self._redis = redis
        self._queue_set_name = "internal::queue"
        self._task_ttl = task_ttl

    async def _generate_id(self) -> int:
        return await self._redis.incr("internal::id_counter")

    def _get_task_key(self, task_id: int) -> str:
        return f"task::{task_id}"

    def _get_task_name_key(self, task_name: str) -> str:
        return f"task_name::{task_name}"

    def _get_task_name_from_key(self, key: str) -> str:
        return key.replace("task_name::", "", 1)

    def _get_task_score(self, task: Task) -> int:
        # Values in redis sorted sets with the same score are stored lexicographically
        # So in order for a queue to be ordered by priority then by the ID
        # we can define score as (priority<<N + task_id)
        return (task.priority.value << SCORE_PRIORITY_BIT_OFFSET) + task.id

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_tasks(self) -> list[Task]:
        tasks = []
        async for key in self._redis.scan_iter("task_name::*"):
            tasks += await self.get_task_instances(
                self._get_task_name_from_key(key.decode())
            )
        return sorted(tasks, key=lambda x: x.id, reverse=True)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_task_instances(self, task_name: str) -> list[Task]:
        task_keys = await self._redis.smembers(self._get_task_name_key(task_name))
        return sorted(
            [Task.parse_raw(task) for task in await self._redis.mget(task_keys)],
            key=lambda x: x.id,
            reverse=True,
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_task_instance(self, id: int) -> Task:
        task = await self._redis.get(self._get_task_key(id))
        if task is None:
            raise TaskNotFoundError()
        return Task.parse_raw(task)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def enqueue_task(self, task: Task) -> Task:
        task.id = await self._generate_id()
        task_key = self._get_task_key(task.id)
        pipe = self._redis.pipeline()
        pipe.set(task_key, task.json(), ex=self._task_ttl)
        pipe.sadd(self._get_task_name_key(task.task_name), task_key)
        pipe.zadd(self._queue_set_name, {task_key: self._get_task_score(task)})
        await pipe.execute()
        return task

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def update_task(self, task: Task) -> Task:
        task_key = self._get_task_key(task.id)
        await self._redis.set(task_key, task.json(), ex=self._task_ttl, xx=True)
        return task

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def dequeue_task(self) -> Task | None:
        tasks = await self._redis.zpopmin(self._queue_set_name)
        if not tasks:
            return None
        task_key, _ = tasks[0]
        task = await self._redis.get(task_key)
        if task is None:
            raise TaskNotFoundError()
        return Task.parse_raw(task)

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def delete_old_tasks(self, keep_last: int = 50) -> None:
        async for key in self._redis.scan_iter("task_name::*"):
            task_instances = sorted(
                await self.get_task_instances(
                    self._get_task_name_from_key(key.decode())
                ),
                key=lambda x: x.id,
                reverse=True,
            )
            for task in task_instances[keep_last:]:
                task_key = self._get_task_key(task.id)
                pipe = self._redis.pipeline()
                pipe.delete(task_key)
                pipe.srem(key, task_key)
                await pipe.execute()

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    @override
    async def get_queue_len(self) -> int:
        return await self._redis.zcount(self._queue_set_name, 0, "+inf")
