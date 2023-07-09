import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel

from sneakpeek.queue.model import TaskPriority

PeriodicTaskId = str


def generate_id() -> PeriodicTaskId:
    return str(uuid4())


class TaskSchedule(str, Enum):
    """
    Periodic task schedule options. Note that it's disallowed to have 2 concurrent
    task, so if there's an active task new one won't be scheduled
    """

    INACTIVE = "inactive"  #: Scraper won't be automatically scheduled
    EVERY_SECOND = "every_second"  #: Scraper will be scheduled every second
    EVERY_MINUTE = "every_minute"  #: Scraper will be scheduled every minute
    EVERY_HOUR = "every_hour"  #: Scraper will be scheduled every hour
    EVERY_DAY = "every_day"  #: Scraper will be scheduled every day
    EVERY_WEEK = "every_week"  #: Scraper will be scheduled every week
    EVERY_MONTH = "every_month"  #: Scraper will be scheduled every month
    CRONTAB = "crontab"  #: Specify crontab when scraper should be scheduled


class PeriodicTask(BaseModel):
    id: PeriodicTaskId  #: Task unique ID
    name: str  #: Task name - used to disallow concurrent execution of the task and to defined unique series of tasks
    handler: str  #: Task handler name
    priority: TaskPriority  #: Task priority
    payload: str  #: Serialized task payload
    schedule: TaskSchedule  #: Task Schedule
    schedule_crontab: str | None = None  #: Task schedule crontab
    timeout: timedelta | None = None  #: Task timeout


class Lease(BaseModel):
    """Global lease metadata"""

    name: str  #: Lease name (resource name to be locked)
    owner_id: str  #: ID of the acquirer (should be the same if you already have the lease and want to prolong it)
    acquired: datetime  #: Time when the lease was acquired
    acquired_until: datetime  #: Time until the lease is acquired


class LeaseStorageABC(ABC):
    """Global lease storage abstract class"""

    @abstractmethod
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        """Try to acquire lease (global lock).

        Args:
            lease_name (str): Lease name (resource name to be locked)
            owner_id (str): ID of the acquirer (should be the same if you already have the lease and want to prolong it)
            acquire_for (timedelta): For how long lease will be acquired

        Returns:
            Lease | None: Lease metadata if it was acquired, None otherwise
        """
        ...

    @abstractmethod
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        """Release lease (global lock)

        Args:
            lease_name (str): Lease name (resource name to be unlocked)
            owner_id (str): ID of the acquirer
        """
        ...


class PeriodicTasksStorageABC(ABC):
    @abstractmethod
    async def get_periodic_tasks(self) -> list[PeriodicTask]:
        ...


class StaticPeriodicTasksStorage(PeriodicTasksStorageABC):
    def __init__(self, tasks: list[PeriodicTask]) -> None:
        self.tasks = tasks

    async def get_periodic_tasks(self) -> list[PeriodicTask]:
        return self.tasks


class MultiPeriodicTasksStorage(PeriodicTasksStorageABC):
    def __init__(self, storages: list[PeriodicTasksStorageABC]) -> None:
        self.storages = storages

    async def get_periodic_tasks(self) -> list[PeriodicTask]:
        return sum(
            await asyncio.gather(
                *[storage.get_periodic_tasks() for storage in self.storages]
            ),
            [],
        )


class SchedulerABC(ABC):
    @abstractmethod
    async def enqueue_task(
        self,
        task_id: PeriodicTaskId,
        priority: TaskPriority,
    ) -> None:
        ...

    @abstractmethod
    async def start_scheduling_task(self, task: PeriodicTask) -> None:
        ...

    @abstractmethod
    async def stop_scheduling_task(self, task: PeriodicTask) -> None:
        ...

    @abstractmethod
    async def update_tasks(self) -> None:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...
