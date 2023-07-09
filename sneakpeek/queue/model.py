from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel


class TaskNotFoundError(jsonrpc.BaseError):
    CODE = 5001
    MESSAGE = "Task not found"


class TaskHasActiveRunError(jsonrpc.BaseError):
    CODE = 10000
    MESSAGE = "Concurrent execution of the task is disallowed"


class TaskPingNotStartedError(jsonrpc.BaseError):
    CODE = 10001
    MESSAGE = "Failed to ping not started task"


class TaskPingFinishedError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Tried to ping finished task"


class TaskTimedOut(jsonrpc.BaseError):
    CODE = 10003
    MESSAGE = "Task has timed out"


class UnknownTaskHandlerError(jsonrpc.BaseError):
    CODE = 10004
    MESSAGE = "Unknown task handler error"


class TaskStatus(str, Enum):
    """Scraper job status"""

    PENDING = "pending"  #: Task is in the queue
    #: Task dequeued by the worker and is being processed
    STARTED = "started"
    FAILED = "failed"  #: Task failed
    SUCCEEDED = "succeeded"  #: Task succeeded
    DEAD = "dead"  #: Task was inactive for a while, so scheduler marked it as dead and scheduler can schedule the task again
    KILLED = "killed"  #: Task was killed by the user


class TaskPriority(Enum):
    """Priority of the scraper job"""

    UTMOST = 0  #:
    HIGH = 1  #:
    NORMAL = 2  #:


class Task(BaseModel):
    """Queue task state"""

    id: int  #: Task unique identifier
    task_name: str  #: Task name (used to disallow concurrent execution of the task)
    task_handler: str  #: Name of the task handler
    status: TaskStatus  #: Task status
    priority: TaskPriority  #: Task priority
    created_at: datetime  #: When the task was created and enqueued
    #: When the task was dequeued and started being processed by the worker
    started_at: datetime | None = None
    last_active_at: datetime | None = None  #: When the task last sent heartbeat
    finished_at: datetime | None = None  #: When the task finished
    payload: str | None = None  #: Serialized task payload
    result: str | None = None  #: Serialised task result
    timeout: timedelta | None = None  #: Task timeout


class EnqueueTaskRequest(BaseModel):
    """Enqueue request"""

    task_name: str  #: Task name (used to disallow concurrent execution of the task)
    task_handler: str  #: Name of the task handler
    priority: TaskPriority  #: Task priority
    payload: str  #: Serialized task payload
    timeout: timedelta | None = None  #: Task timeout


class QueueABC(ABC):
    """Task priority queue"""

    @abstractmethod
    async def enqueue(self, request: EnqueueTaskRequest) -> Task:
        """Enqueue task

        Args:
            request (EnqueueTaskRequest): metadata of task to enqueue

        Returns:
            Task: Enqueued task metadata

        Raises:
            TaskHasActiveRunError: Error when there are other tasks with the same name in ``PENDING`` or ``STARTED`` state
        """
        ...

    @abstractmethod
    async def dequeue(self) -> Task | None:
        """Try to dequeue a task from the queue.

        Returns:
            Task: Dequeued task metadata
        """
        ...

    @abstractmethod
    async def update_task(self, task: Task) -> Task:
        """
        Update task metadata

        Args:
            task (Task): updated task metadata to save

        Returns:
            Task: Updated task metadata

        Raises:
            TaskNotFoundError: Raised when task doesn't exist
        """
        ...

    @abstractmethod
    async def get_queue_len(self) -> int:
        """
        Get number of pending items in the queue
        """
        ...

    @abstractmethod
    async def ping_task(self, id: int) -> Task:
        """Send a heartbeat for the task

        Args:
            id (int): Task ID

        Returns:
            Task: Updated task metadata

        Raises:
            TaskNotFoundError: Raised if task doesn't exist
            TaskNotStartedError: Raised if task is still in the ``PENDING`` state
            TaskPingFinishedError: Raised if task is in finished state (e.g. ``DEAD``)
        """
        ...

    @abstractmethod
    async def kill_dead_tasks(self) -> list[Task]:
        """Kill dead tasks

        Returns:
            list[Task]: List of killed dead tasks
        """
        ...

    @abstractmethod
    async def delete_old_tasks(self, keep_last: int = 50) -> None:
        """Delete old historical tasks

        Args:
            keep_last (int, optional): How many tasks to keep. Defaults to 50.
        """
        ...

    @abstractmethod
    async def get_task_instances(self, task_name: str) -> list[Task]:
        """
        Get task instances by task name

        Args:
            task_name (str): Task name

        Returns:
            list[Task]: List of task instances
        """
        ...

    @abstractmethod
    async def get_task_instance(self, task_id: int) -> Task:
        """
        Get task instance by ID

        Args:
            task_id (int): Task ID

        Returns:
            Task: Task instance
        """
        ...


class QueueStorageABC(ABC):
    """Priority queue storage"""

    @abstractmethod
    async def get_tasks(self) -> list[Task]:
        """
        Get all task instances

        Returns:
            list[Task]: List of task instances
        """
        ...

    @abstractmethod
    async def get_task_instances(self, task_name: str) -> list[Task]:
        """
        Get task instances by task name

        Args:
            task_name (str): Task name

        Returns:
            list[Task]: List of task instances
        """
        ...

    @abstractmethod
    async def get_task_instance(self, id: int) -> Task:
        """
        Get task instance by ID

        Args:
            id (int): Task ID

        Returns:
            Task: Found task metadata

        Raises:
            TaskNotFoundError: Raised when task doesn't exist
        """
        ...

    @abstractmethod
    async def enqueue_task(self, task: Task) -> Task:
        """
        Add a new task instance and put it into the queue

        Args:
            task (Task): task to add

        Returns:
            Task: Created task metadata
        """
        ...

    @abstractmethod
    async def update_task(self, task: Task) -> Task:
        """
        Update task metadata

        Args:
            task (Task): updated task metadata to save

        Returns:
            Task: Updated task metadata

        Raises:
            TaskNotFoundError: Raised when task doesn't exist
        """
        ...

    @abstractmethod
    async def dequeue_task(self) -> Task | None:
        """Try to dequeue pending task

        Returns:
            Task | None: First pending task or None if the queue is empty
        """
        ...

    @abstractmethod
    async def delete_old_tasks(self, keep_last: int = 50) -> None:
        """Delete old historical tasks

        Args:
            keep_last (int, optional): How many tasks to keep. Defaults to 50.
        """
        ...

    @abstractmethod
    async def get_queue_len(self) -> int:
        """
        Get number of pending items in the queue
        """
        ...


class TaskHandlerABC:
    @abstractmethod
    def name(self) -> int:
        """
        Task names that handler can process
        """
        ...

    @abstractmethod
    async def process(self, task: Task) -> str:
        """Process queue task

        Args:
            task (Task): task metadata

        Returns:
            str: task processing result
        """
        ...
