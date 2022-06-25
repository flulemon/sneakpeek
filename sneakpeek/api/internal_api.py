from datetime import datetime

import fastapi_jsonrpc as jsonrpc
from fastapi import Body

from sneakpeek.lib.models import Lease, ScraperRun, ScraperRunPriority
from sneakpeek.lib.queue import Queue, ScraperHasActiveRunError
from sneakpeek.lib.storage.base import (
    ScraperNotFoundError,
    ScraperRunNotFoundError,
    Storage,
)


def get_internal_api_entrypoint(storage: Storage, queue: Queue) -> jsonrpc.Entrypoint:
    entrypoint = jsonrpc.Entrypoint("/api/internal/v1/jsonrpc")

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperHasActiveRunError])
    async def enqueue_scraper(
        scraper_id: int = Body(...),
        priority: ScraperRunPriority = Body(...),
    ) -> ScraperRun:
        return await queue.enqueue(scraper_id=scraper_id, priority=priority)

    @entrypoint.method()
    async def dequeue_scraper_run() -> ScraperRun | None:
        return await queue.dequeue()

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperRunNotFoundError])
    async def update_scraper_run(scraper_run: ScraperRun = Body(...)) -> ScraperRun:
        return await storage.update_scraper_run(scraper_run)

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperRunNotFoundError])
    async def ping_scraper_run(
        scraper_id: int = Body(...),
        scraper_run_id: int = Body(...),
    ) -> ScraperRun:
        return await storage.ping_scraper_run(scraper_id, scraper_run_id)

    @entrypoint.method(errors=[ScraperNotFoundError, ScraperRunNotFoundError])
    async def maybe_acquire_lease(
        lease_name: str = Body(...),
        owner_id: str = Body(...),
        acquire_until: datetime = Body(...),
    ) -> Lease | None:
        return await storage.maybe_acquire_lease(lease_name, owner_id, acquire_until)

    return entrypoint
