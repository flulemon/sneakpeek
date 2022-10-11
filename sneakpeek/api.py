from typing import List

import fastapi_jsonrpc as jsonrpc
from fastapi import Body

from sneakpeek.lib.errors import ScraperHasActiveRunError, ScraperNotFoundError
from sneakpeek.lib.models import Scraper, ScraperRun, ScraperRunPriority
from sneakpeek.lib.queue import Queue, QueueABC
from sneakpeek.lib.storage.base import Storage
from sneakpeek.scraper import ScraperABC


def get_public_api_entrypoint(
    storage: Storage,
    queue: Queue,
    handlers: List[ScraperABC],
) -> jsonrpc.Entrypoint:
    entrypoint = jsonrpc.Entrypoint("/api/v1/jsonrpc")

    @entrypoint.method()
    async def search_scrapers(
        name_filter: str | None = Body(...),
        max_items: int | None = Body(...),
        last_id: int | None = Body(...),
    ) -> List[Scraper]:
        return await storage.search_scrapers(name_filter, max_items, last_id)

    @entrypoint.method()
    async def get_scrapers() -> List[Scraper]:
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
    async def get_scraper_runs(scraper_id: int = Body(...)) -> List[ScraperRun]:
        return await storage.get_scraper_runs(scraper_id)

    @entrypoint.method()
    async def get_scraper_handlers() -> List[str]:
        return [handler.name for handler in handlers]

    return entrypoint


def create_api(
    storage: Storage,
    queue: QueueABC,
    handlers: List[ScraperABC],
) -> jsonrpc.API:
    app = jsonrpc.API()
    app.bind_entrypoint(get_public_api_entrypoint(storage, queue, handlers))
    return app
