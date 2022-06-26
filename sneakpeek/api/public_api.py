from typing import List

import fastapi_jsonrpc as jsonrpc
from fastapi import Body

from sneakpeek.lib.models import Scraper, ScraperRun
from sneakpeek.lib.storage.base import ScraperNotFoundError, Storage


def get_public_api_entrypoint(storage: Storage) -> jsonrpc.Entrypoint:
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

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def update_scraper(scraper: Scraper = Body(...)) -> Scraper:
        return await storage.update_scraper(scraper)

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def delete_scraper(id: int = Body(...)) -> Scraper:
        return await storage.delete_scraper(id)

    @entrypoint.method(errors=[ScraperNotFoundError])
    async def get_scraper_runs(scraper_id: int = Body(...)) -> List[ScraperRun]:
        return await storage.get_scraper_runs(scraper_id)

    return entrypoint
