import logging
from datetime import datetime, timedelta

from typing_extensions import override

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueABC,
    QueueStorageABC,
    Task,
    TaskHasActiveRunError,
    TaskPingFinishedError,
    TaskPingNotStartedError,
    TaskStatus,
)

DEFAULT_DEAD_TIMEOUT = timedelta(minutes=5)


class Queue(QueueABC):
    def __init__(
        self,
        storage: QueueStorageABC,
        dead_task_timeout: timedelta = DEFAULT_DEAD_TIMEOUT,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.storage = storage
        self.dead_task_timeout = dead_task_timeout

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def enqueue(self, request: EnqueueTaskRequest) -> Task:
        existing_tasks = await self.storage.get_task_instances(request.task_name)
        if any(
            t
            for t in existing_tasks
            if t.status in (TaskStatus.STARTED, TaskStatus.PENDING)
        ):
            raise TaskHasActiveRunError()
        task = Task(
            id=0,
            task_name=request.task_name,
            task_handler=request.task_handler,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            payload=request.payload,
            priority=request.priority,
            timeout=request.timeout,
        )
        return await self.storage.enqueue_task(task)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def dequeue(self) -> Task | None:
        return await self.storage.dequeue_task()

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def get_queue_len(self) -> int:
        return await self.storage.get_queue_len()

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def ping_task(self, id: int) -> Task:
        task = await self.storage.get_task_instance(id)
        if task.status == TaskStatus.PENDING:
            raise TaskPingNotStartedError()
        if task.status != TaskStatus.STARTED:
            raise TaskPingFinishedError()
        task.last_active_at = datetime.utcnow()
        return await self.storage.update_task(task)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def kill_dead_tasks(self) -> list[Task]:
        tasks = await self.storage.get_tasks()
        killed = []
        for task in tasks:
            if self._is_task_dead(task):
                task.status = TaskStatus.DEAD
                task.finished_at = datetime.utcnow()
                killed.append(await self.storage.update_task(task))
        return killed

    def _is_task_dead(self, task: Task) -> bool:
        if task.status != Task.STARTED:
            return False
        activity_timestamps = [
            task.last_active_at,
            task.started_at,
            task.created_at,
        ]
        for ts in activity_timestamps:
            if ts and datetime.utcnow() - ts > self._dead_timeout:
                return True
        return False

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def delete_old_tasks(self, keep_last: int = 50) -> None:
        await self.storage.delete_old_tasks(keep_last)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def update_task(self, task: Task) -> Task:
        return await self.storage.update_task(task)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def get_task_instances(self, task_name: str) -> list[Task]:
        return await self.storage.get_task_instances(task_name)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    @override
    async def get_task_instance(self, task_id: int) -> Task:
        return await self.storage.get_task_instance(task_id)
