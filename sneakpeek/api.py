import os
import pathlib

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

from sneakpeek.errors import ScraperHasActiveRunError, ScraperNotFoundError
from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.models import Scraper, ScraperJob, ScraperJobPriority, ScraperSchedule
from sneakpeek.queue import Queue, QueueABC
from sneakpeek.scraper_handler import ScraperHandler
from sneakpeek.storage.base import ScraperJobsStorage, ScrapersStorage


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
    scrapers_storage: ScrapersStorage,
    jobs_storage: ScraperJobsStorage,
    queue: Queue,
    handlers: list[ScraperHandler],
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
    async def search_scrapers(
        name_filter: str | None = Body(...),
        max_items: int | None = Body(...),
        last_id: int | None = Body(...),
    ) -> list[Scraper]:
        return await scrapers_storage.search_scrapers(name_filter, max_items, last_id)

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scrapers() -> list[Scraper]:
        return await scrapers_storage.get_scrapers()

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scraper(id: int = Body(...)) -> Scraper:
        return await scrapers_storage.get_scraper(id)

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def create_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await scrapers_storage.create_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperHasActiveRunError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def enqueue_scraper(
        scraper_id: int = Body(...),
        priority: ScraperJobPriority = Body(...),
    ) -> ScraperJob:
        return await queue.enqueue(scraper_id, priority)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def update_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await scrapers_storage.update_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def delete_scraper(id: int = Body(...)) -> Scraper:
        return await scrapers_storage.delete_scraper(id)

    @entrypoint.method(errors=[ScraperNotFoundError])
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scraper_jobs(scraper_id: int = Body(...)) -> list[ScraperJob]:
        return await jobs_storage.get_scraper_jobs(scraper_id)

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_scraper_handlers() -> list[str]:
        return [handler.name for handler in handlers]

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_schedules() -> list[str]:
        return [schedule.value for schedule in ScraperSchedule]

    @entrypoint.method()
    @count_invocations(subsystem="api")
    @measure_latency(subsystem="api")
    async def get_priorities() -> list[Priority]:
        return [
            Priority(name=priority.name, value=priority.value)
            for priority in ScraperJobPriority
        ]

    @entrypoint.method()
    async def is_read_only() -> bool:
        return await scrapers_storage.is_read_only()

    return entrypoint


def create_api(
    scrapers_storage: ScrapersStorage,
    jobs_storage: ScraperJobsStorage,
    queue: QueueABC,
    handlers: list[ScraperHandler],
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
            scrapers_storage,
            jobs_storage,
            queue,
            handlers,
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
