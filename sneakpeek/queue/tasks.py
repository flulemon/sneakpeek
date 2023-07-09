import json

from sneakpeek.queue.model import QueueABC, Task, TaskHandlerABC, TaskPriority
from sneakpeek.scheduler.model import (
    PeriodicTask,
    StaticPeriodicTasksStorage,
    TaskSchedule,
    generate_id,
)

KILL_DEAD_TASKS_TASK_NAME = "internal::queue::kill_dead_tasks"
DELETE_OLD_TASKS_TASK_NAME = "internal::queue::delete_old_tasks"


class KillDeadTasksHandler(TaskHandlerABC):
    def __init__(self, queue: QueueABC) -> None:
        self.queue = queue

    def name(self) -> int:
        return KILL_DEAD_TASKS_TASK_NAME

    async def process(self, task: Task) -> str:
        killed = await self.queue.kill_dead_tasks()
        return json.dumps(
            {
                "success": True,
                "killed": [item.id for item in killed],
            },
            indent=4,
        )


class DeleteOldTasksHandler(TaskHandlerABC):
    def __init__(self, queue: QueueABC) -> None:
        self.queue = queue

    def name(self) -> int:
        return DELETE_OLD_TASKS_TASK_NAME

    async def process(self, task: Task) -> str:
        await self.queue.delete_old_tasks()
        return json.dumps({"success": True}, indent=4)


queue_periodic_tasks = StaticPeriodicTasksStorage(
    tasks=[
        PeriodicTask(
            id=generate_id(),
            name=KILL_DEAD_TASKS_TASK_NAME,
            handler=KILL_DEAD_TASKS_TASK_NAME,
            priority=TaskPriority.NORMAL,
            payload="",
            schedule=TaskSchedule.EVERY_HOUR,
        ),
        PeriodicTask(
            id=generate_id(),
            name=DELETE_OLD_TASKS_TASK_NAME,
            handler=DELETE_OLD_TASKS_TASK_NAME,
            priority=TaskPriority.NORMAL,
            payload="",
            schedule=TaskSchedule.EVERY_HOUR,
        ),
    ]
)
