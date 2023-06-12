import asyncio
import logging
from asyncio import Lock
from datetime import datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from prometheus_client import Gauge
from typing_extensions import override

from sneakpeek.metrics import count_invocations, measure_latency, replicas_gauge
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueABC,
    TaskHasActiveRunError,
    TaskPriority,
)
from sneakpeek.scheduler.model import (
    Lease,
    LeaseStorageABC,
    PeriodicTask,
    PeriodicTaskId,
    PeriodicTasksStorageABC,
    SchedulerABC,
    TaskSchedule,
)

DEFAULT_LEASE_DURATION = timedelta(minutes=1)
DEFAULT_TASKS_POLL_DELAY = timedelta(seconds=5)

queue_length_gauge = Gauge(
    name="queue_length",
    documentation="Number of pending tasks",
    namespace="sneakpeek",
)


class Scheduler(SchedulerABC):
    def __init__(
        self,
        tasks_storage: PeriodicTasksStorageABC,
        lease_storage: LeaseStorageABC,
        queue: QueueABC,
        loop: asyncio.AbstractEventLoop | None = None,
        tasks_poll_delay: timedelta = DEFAULT_TASKS_POLL_DELAY,
        lease_duration: timedelta = DEFAULT_LEASE_DURATION,
    ) -> None:
        self.tasks_storage = tasks_storage
        self.lease_storage = lease_storage
        self.queue = queue
        self.tasks_poll_delay = tasks_poll_delay.total_seconds()
        self.lease_duration = lease_duration
        self.loop = loop or asyncio.get_event_loop()

        self.lease_name = "sneakpeek:scheduler"
        self.owner_id = str(uuid4())
        self.scheduler = AsyncIOScheduler()
        self.lease: Lease | None = None
        self.lock = Lock()
        self.tasks: dict[PeriodicTaskId, PeriodicTask] = {}
        self.logger = logging.getLogger(__name__)
        self.update_cycle_task: asyncio.Task | None = None

    @property
    def _is_lease_acquired(self) -> bool:
        return (
            self.lease
            and self.lease.acquired
            and datetime.utcnow() < self.lease.acquired_until
        )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    @override
    async def enqueue_task(
        self,
        task_id: PeriodicTaskId,
        priority: TaskPriority,
    ) -> None:
        if not self._is_lease_acquired:
            self.logger.debug(
                f"Couldn't enqueue task id={task_id} because lease is not acquired"
            )
            return
        task = self.tasks.get(task_id)
        if not task:
            self.logger.warning(f"Tried to enqueue unknown task: {task_id}")
            return

        formatted_task_name = f"{task.handler}::{task.name}::{task.id}"
        self.logger.debug(f"Trying to enqueue task {formatted_task_name}")
        try:
            enqueued = await self.queue.enqueue(
                EnqueueTaskRequest(
                    task_name=task.name,
                    task_handler=task.handler,
                    priority=priority,
                    payload=task.payload,
                    timeout=task.timeout,
                ),
            )
            self.logger.info(
                f"Successfully enqueued task {formatted_task_name}: {enqueued.id}"
            )
        except TaskHasActiveRunError:
            self.logger.debug(
                f"Won't enqueue {formatted_task_name} because there's an active task",
                exc_info=True,
            )
        except Exception:
            self.logger.exception(f"Failed to enqueue {formatted_task_name}")

    async def _get_task_trigger(self, task: PeriodicTask) -> BaseTrigger | None:
        start_date = datetime.min
        tasks = await self.queue.get_task_instances(task.name)
        if tasks:
            last_run = sorted(tasks, key=lambda x: x.id, reverse=True)[0]
            start_date = last_run.finished_at
        match task.schedule:
            case TaskSchedule.CRONTAB:
                return CronTrigger.from_crontab(task.schedule_crontab)
            case TaskSchedule.EVERY_HOUR:
                return IntervalTrigger(hours=1, start_date=start_date)
            case TaskSchedule.EVERY_DAY:
                return IntervalTrigger(days=1, start_date=start_date)
            case TaskSchedule.EVERY_WEEK:
                return IntervalTrigger(weeks=1, start_date=start_date)
            case TaskSchedule.EVERY_MONTH:
                return IntervalTrigger(days=30, start_date=start_date)
            case TaskSchedule.EVERY_MINUTE:
                return IntervalTrigger(minutes=1, start_date=start_date)
            case TaskSchedule.EVERY_SECOND:
                return IntervalTrigger(seconds=1, start_date=start_date)
            case TaskSchedule.INACTIVE:
                return None
            case _:
                raise ValueError(f"Unsupported Scraper schedule: {task.schedule}")

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    @override
    async def start_scheduling_task(self, task: PeriodicTask) -> None:
        logging.info(f"Starting scheduling task {task.name}::{task.id}")
        job_id = f"scheduler:task:{task.id}"
        trigger = await self._get_task_trigger(task)
        self.tasks[task.id] = task
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        if trigger:
            self.scheduler.add_job(
                self.enqueue_task,
                trigger,
                id=job_id,
                args=(task.id, task.priority),
            )

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    @override
    async def stop_scheduling_task(self, task: PeriodicTask) -> None:
        logging.info(f"Stopping scheduling task {task.name}::{task.id}")
        self.scheduler.remove_job(f"scheduler:task:{task.id}")
        del self.tasks[task.id]

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    @override
    async def update_tasks(self) -> None:
        """Poll storage for all existing periodic tasks and update corresponding scheduler jobs"""
        tasks = await self.tasks_storage.get_periodic_tasks()
        index = {task.id: task for task in tasks}
        for existing in self.tasks.values():
            if (
                existing.id not in index
                or index[existing.id].schedule == TaskSchedule.INACTIVE
            ):
                await self.stop_scheduling_task(existing)
            elif self.tasks[existing.id] != index[existing.id]:
                await self.start_scheduling_task(index[existing.id])

        for task in index.values():
            if task.id not in self.tasks and task.schedule != TaskSchedule.INACTIVE:
                await self.start_scheduling_task(task)

    @measure_latency(subsystem="scheduler")
    @count_invocations(subsystem="scheduler")
    async def _on_tick(self) -> None:
        """Periodic job that:

        * Tries to acquire lease to ensure that there's only single active scheduler replica that can enqueue jobs
        * Updates internal (APScheduler) jobs that enqueue scrapers
        """

        replicas_gauge.labels(type="total_scheduler").set(1)
        try:
            self.logger.debug("Starting scheduler update cycle")
            self.logger.debug("Trying to acquire lease")
            self.lease = await self.lease_storage.maybe_acquire_lease(
                self.lease_name,
                self.owner_id,
                self.lease_duration,
            )
            replicas_gauge.labels(type="active_scheduler").set(bool(self.lease))
            if not self.lease:
                return
            self.logger.info(
                f"Successfully acquired lease until {self.lease.acquired_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await self.update_tasks()
            queue_length_gauge.set(await self.queue.get_queue_len())
        except Exception:
            self.logger.exception("Scheduler on tick function failed")

    async def _update_cycle(self):
        while True:
            self.logger.info("Scheduler on tick")
            await self._on_tick()
            await asyncio.sleep(self.tasks_poll_delay)
            self.logger.info("Scheduler after on tick")
        self.logger.info("Scheduler exiting on tick")

    @override
    def start(self) -> None:
        self.logger.info("Starting scheduler")
        self.update_cycle_task = self.loop.create_task(self._update_cycle())
        self.scheduler.start()

    @override
    def stop(self) -> None:
        self.logger.info("Stopping scheduler")
        self.scheduler.shutdown(wait=False)
        if self.update_cycle_task:
            self.update_cycle_task.cancel()
