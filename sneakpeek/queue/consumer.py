import asyncio
import logging
from datetime import datetime, timedelta
from traceback import format_exc

from prometheus_client import Counter

from sneakpeek.logging import task_context
from sneakpeek.metrics import (
    count_invocations,
    delay_histogram,
    measure_latency,
    replicas_gauge,
)
from sneakpeek.queue.model import (
    QueueABC,
    Task,
    TaskHandlerABC,
    TaskPingFinishedError,
    TaskStatus,
    TaskTimedOut,
    UnknownTaskHandlerError,
)

POLL_DELAY = timedelta(milliseconds=100)
TASK_PING_DELAY = timedelta(seconds=1)


task_executed = Counter(
    name="task_executed",
    documentation="Tasks executed",
    namespace="sneakpeek",
    labelnames=["handler", "name", "status"],
)


class Consumer:
    def __init__(
        self,
        queue: QueueABC,
        handlers: list[TaskHandlerABC],
        loop: asyncio.AbstractEventLoop | None = None,
        max_concurrency: int = 50,
        poll_delay: timedelta = POLL_DELAY,
        ping_delay: timedelta = TASK_PING_DELAY,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.queue = queue
        self.handlers = {handler.name(): handler for handler in handlers}
        self.max_concurrency = max_concurrency
        self.active: set[asyncio.Task] = set()
        self.loop = loop or asyncio.get_event_loop()
        self.ping_delay = ping_delay.total_seconds()
        self.poll_delay = poll_delay.total_seconds()
        self.running = False
        self.cycle_task: asyncio.Task | None = None

    async def _handle_task(self, handler: TaskHandlerABC, task: Task) -> str:
        with task_context(task):
            return await handler.process(task)

    @count_invocations(subsystem="consumer")
    async def process_task(self, task: Task) -> None:
        delay_histogram.labels(type="time_spent_in_queue").observe(
            (datetime.utcnow() - task.created_at).total_seconds()
        )
        handler_task: asyncio.Task | None = None
        self.logger.info(f"Executing task id={task.id}")
        try:
            task.started_at = datetime.utcnow()
            task.status = TaskStatus.STARTED
            task = await self.queue.update_task(task)

            if task.task_handler not in self.handlers:
                raise UnknownTaskHandlerError(task.task_handler)
            handler = self.handlers[task.task_handler]
            handler_task = self.loop.create_task(self._handle_task(handler, task))

            while not handler_task.done():
                if task.timeout and datetime.utcnow() - task.started_at > task.timeout:
                    raise TaskTimedOut()
                task = await self.queue.ping_task(task.id)
                await asyncio.sleep(self.ping_delay)

            result = handler_task.result()
            task.finished_at = datetime.utcnow()
            task.status = TaskStatus.SUCCEEDED
            task.result = result
            self.logger.info(f"Successfully executed task id={task.id}")
        except TaskPingFinishedError:
            if handler_task and not handler_task.done():
                handler_task.cancel()
            self.logger.exception(f"Seems like task {task.id} was killed")
        except Exception:
            if handler_task and not handler_task.done():
                handler_task.cancel()
            self.logger.exception(f"Failed to execute {task.id}")
            task.finished_at = datetime.utcnow()
            task.status = TaskStatus.FAILED
            task.result = format_exc()
        finally:
            try:
                task = await self.queue.update_task(task)
                task_executed.labels(
                    handler=task.task_handler,
                    name=task.task_name,
                    status=task.status.name.lower(),
                )
            except Exception:
                self.logger.exception(f"Failed to update task {task.id}")

    @measure_latency(subsystem="consumer")
    @count_invocations(subsystem="consumer")
    async def consume(self):
        replicas_gauge.labels(type="active_tasks").set(len(self.active))
        if len(self.active) >= self.max_concurrency:
            self.logger.debug(
                f"Not dequeuing any tasks because worker has reached max concurrency,"
                f" there are {len(self.active)} of active tasks"
            )
            return False

        dequeued = await self.queue.dequeue()
        if not dequeued:
            self.logger.debug("No pending tasks in the queue")
            return False

        self.logger.info(f"Dequeued a task id={dequeued.id}")
        task_handle = self.loop.create_task(self.process_task(dequeued))
        self.active.add(task_handle)
        task_handle.add_done_callback(self.active.discard)
        return True

    async def _cycle(self):
        while self.running:
            if not await self.consume():
                await asyncio.sleep(self.poll_delay)

    def start(self):
        self.running = True
        self.cycle_task = self.loop.create_task(self._cycle())

    def stop(self):
        self.running = False
        if self.cycle_task:
            self.cycle_task.cancel()
