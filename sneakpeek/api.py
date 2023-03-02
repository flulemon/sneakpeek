import pathlib

import fastapi_jsonrpc as jsonrpc
from fastapi import Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sneakpeek.lib.errors import ScraperHasActiveRunError, ScraperNotFoundError
from sneakpeek.lib.models import (
    Scraper,
    ScraperRun,
    ScraperRunPriority,
    ScraperSchedule,
)
from sneakpeek.lib.queue import Queue, QueueABC
from sneakpeek.lib.storage.base import Storage
from sneakpeek.scraper_handler import ScraperHandler


class Priority(BaseModel):
    name: str
    value: int


def get_public_api_entrypoint(
    storage: Storage,
    queue: Queue,
    handlers: list[ScraperHandler],
) -> jsonrpc.Entrypoint:
    entrypoint = jsonrpc.Entrypoint("/api/v1/jsonrpc")

    @entrypoint.method()
    async def search_scrapers(
        name_filter: str | None = Body(...),
        max_items: int | None = Body(...),
        last_id: int | None = Body(...),
    ) -> list[Scraper]:
        return await storage.search_scrapers(name_filter, max_items, last_id)

    @entrypoint.method()
    async def get_scrapers() -> list[Scraper]:
        return await storage.get_scrapers()

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def get_scraper(id: int = Body(...)) -> Scraper:
        return await storage.get_scraper(id)

    @entrypoint.method()
    async def create_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await storage.create_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperHasActiveRunError])
    async def enqueue_scraper(
        scraper_id: int = Body(...),
        priority: ScraperRunPriority = Body(...),
    ) -> ScraperRun:
        return await queue.enqueue(scraper_id, priority)

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def update_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await storage.update_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def delete_scraper(id: int = Body(...)) -> Scraper:
        return await storage.delete_scraper(id)

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def get_scraper_runs(scraper_id: int = Body(...)) -> list[ScraperRun]:
        return await storage.get_scraper_runs(scraper_id)

    @entrypoint.method()
    async def get_scraper_handlers() -> list[str]:
        return [handler.name for handler in handlers]

    @entrypoint.method()
    async def get_schedules() -> list[str]:
        return [schedule.value for schedule in ScraperSchedule]

    @entrypoint.method()
    async def get_priorities() -> list[Priority]:
        return [
            Priority(name=priority.name, value=priority.value)
            for priority in ScraperRunPriority
        ]

    @entrypoint.method()
    async def is_read_only() -> bool:
        return await storage.is_read_only()

    return entrypoint


def create_api(
    storage: Storage,
    queue: QueueABC,
    handlers: list[ScraperHandler],
) -> jsonrpc.API:
    app = jsonrpc.API()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.bind_entrypoint(get_public_api_entrypoint(storage, queue, handlers))
    app.mount(
        "/",
        StaticFiles(
            directory=f"{pathlib.Path(__file__).parent.resolve()}/static",
            html=True,
        ),
        name="html",
    )
    return app
