import logging
import os
import pathlib
from datetime import timedelta

import fastapi_jsonrpc as jsonrpc
from fastapi import Body, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    generate_latest,
)
from prometheus_client.multiprocess import MultiProcessCollector
from pydantic import BaseModel

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.queue.model import (
    EnqueueTaskRequest,
    QueueABC,
    Task,
    TaskHasActiveRunError,
    TaskPriority,
)
from sneakpeek.scheduler.model import TaskSchedule
from sneakpeek.scraper.ephemeral_scraper_task_handler import EphemeralScraperTask
from sneakpeek.scraper.model import (
    EPHEMERAL_SCRAPER_TASK_HANDLER_NAME,
    SCRAPER_PERIODIC_TASK_HANDLER_NAME,
    CreateScraperRequest,
    Scraper,
    ScraperHandler,
    ScraperId,
    ScraperNotFoundError,
    ScraperStorageABC,
)
from sneakpeek.session_loggers.base import LogLine, SessionLogger


class Priority(BaseModel):
    name: str
    value: int


def metrics(request: Request) -> Response:  # pragma: no cover
    if "prometheus_multiproc_dir" in os.environ:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
    else:
        registry = REGISTRY

    return Response(
        generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
    )


def get_api_entrypoint(
    scraper_storage: ScraperStorageABC,
    queue: QueueABC,
    handlers: list[ScraperHandler],
    session_logger_handler: SessionLogger | None = None,
) -> jsonrpc.Entrypoint:  # pragma: no cover
    """
    Create public JsonRPC API entrypoint (mostly mimics storage and queue API)

    Args:
        storage (Storage): Sneakpeek storage implementation
        queue (Queue): Sneakpeek queue implementation
        handlers (list[ScraperHandler]): List of handlers that implement scraper logic

    Returns:
        jsonrpc.Entrypoint: FastAPI JsonRPC entrypoint
    """
    entrypoint = jsonrpc.Entrypoint("/api/v1/jsonrpc")

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scrapers() -> list[Scraper]:
        return await scraper_storage.get_scrapers()

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scraper(id: ScraperId = Body(...)) -> Scraper:
        return await scraper_storage.get_scraper(id)

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def create_scraper(scraper: CreateScraperRequest = Body(...)) -> Scraper:
        return await scraper_storage.create_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError, TaskHasActiveRunError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def enqueue_scraper(
        scraper_id: ScraperId = Body(...),
        priority: TaskPriority = Body(...),
    ) -> Task:
        return await queue.enqueue(
            EnqueueTaskRequest(
                task_name=scraper_id,
                task_handler=SCRAPER_PERIODIC_TASK_HANDLER_NAME,
                priority=priority,
                payload="",
            )
        )

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def update_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await scraper_storage.update_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def delete_scraper(id: ScraperId = Body(...)) -> Scraper:
        return await scraper_storage.delete_scraper(id)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_task_instances(task_name: str = Body(...)) -> list[Task]:
        return await queue.get_task_instances(task_name)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_task_instance(task_id: int = Body(...)) -> Task:
        return await queue.get_task_instance(task_id)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_task_logs(
        task_id: int = Body(...),
        last_log_line_id: str | None = Body(default=None),
        max_lines: int = Body(default=100),
    ) -> list[LogLine]:
        return await session_logger_handler.read(
            task_id,
            last_log_line_id=last_log_line_id,
            max_lines=max_lines,
        )

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scraper_handlers() -> list[str]:
        return [handler.name for handler in handlers]

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_schedules() -> list[str]:
        return [schedule.value for schedule in TaskSchedule]

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_priorities() -> list[Priority]:
        return [
            Priority(name=priority.name, value=priority.value)
            for priority in TaskPriority
        ]

    @entrypoint.method()
    async def is_read_only() -> bool:
        return scraper_storage.is_read_only()

    @entrypoint.method()
    async def run_ephemeral(
        task: EphemeralScraperTask, priority: TaskPriority = TaskPriority.NORMAL
    ) -> Task:
        return await queue.enqueue(
            EnqueueTaskRequest(
                task_name=EPHEMERAL_SCRAPER_TASK_HANDLER_NAME,
                task_handler=EPHEMERAL_SCRAPER_TASK_HANDLER_NAME,
                priority=priority,
                timeout=timedelta(hours=1),
                payload=task.json(),
            )
        )

    return entrypoint


def create_api(
    scraper_storage: ScraperStorageABC,
    queue: QueueABC,
    handlers: list[ScraperHandler],
    session_logger_handler: logging.Handler | None = None,
) -> jsonrpc.API:  # pragma: no cover
    """
    Create JsonRPC API (FastAPI is used under the hood)

    Args:
        storage (Storage): Sneakpeek storage implementation
        queue (Queue): Sneakpeek queue implementation
        handlers (list[ScraperHandler]): List of handlers that implement scraper logic
    """
    app = jsonrpc.API(docs_url="/api", redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.bind_entrypoint(
        get_api_entrypoint(
            scraper_storage,
            queue,
            handlers,
            session_logger_handler,
        )
    )
    app.add_route("/metrics", metrics)
    app.mount(
        "/docs/",
        StaticFiles(
            directory=f"{pathlib.Path(__file__).parent.resolve()}/static/docs",
            html=True,
        ),
        name="html",
    )
    app.mount(
        "/",
        StaticFiles(
            directory=f"{pathlib.Path(__file__).parent.resolve()}/static/ui",
            html=True,
        ),
        name="html",
    )
    return app
