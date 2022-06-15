import logging
from datetime import datetime

import fastapi_jsonrpc as jsonrpc

from sneakpeek.lib.models import (
    UNSET_ID,
    ScraperRun,
    ScraperRunPriority,
    ScraperRunStatus,
)
from sneakpeek.lib.storage.base import Storage


class ScraperHasActiveRunError(jsonrpc.BaseError):
    CODE = 10000
    MESSAGE = "Scraper has active runs"


class Queue:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._logger = logging.getLogger(__name__)

    async def enqueue(
        self,
        scraper_id: int,
        priority: ScraperRunPriority,
    ) -> ScraperRun:
        scraper = await self._storage.get_scraper(scraper_id)
        if await self._storage.has_unfinished_scraper_runs(scraper_id):
            raise ScraperHasActiveRunError()
        return await self._storage.add_scraper_run(
            ScraperRun(
                id=UNSET_ID,
                scraper=scraper,
                status=ScraperRunStatus.PENDING,
                priority=priority,
                created_at=datetime.utcnow(),
            )
        )

    async def dequeue(self) -> ScraperRun | None:
        return await self._storage.dequeue_scraper_run()
