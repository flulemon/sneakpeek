import logging

from sneakpeek.metrics import count_invocations
from sneakpeek.scraper.context import ScraperContext
from sneakpeek.scraper.models import (
    Middleware,
    Scraper,
    ScraperHandler,
    ScraperId,
    ScraperRunnerABC,
    ScraperStorageABC,
)


class ScraperRunner(ScraperRunnerABC):
    """Default scraper runner implementation that is meant to be used in the Sneakpeek server"""

    def __init__(
        self,
        scraper_storage: ScraperStorageABC,
        middlewares: list[Middleware] | None = None,
    ) -> None:
        """
        Args:
            handlers (list[ScraperHandler]): List of handlers that implement scraper logic
            scrapers_storage (ScrapersStorage): Sneakpeek scrapers storage implementation
            jobs_storage (ScraperJobsStorage): Sneakpeek jobs storage implementation
            middlewares (list[Middleware] | None, optional): List of middleware that will be used by scraper runner. Defaults to None.
        """
        self.logger = logging.getLogger(__name__)
        self.scraper_storage = scraper_storage
        self.middlewares = middlewares

    @count_invocations(subsystem="scraper_runner")
    async def run(self, handler: ScraperHandler, scraper: Scraper) -> str:
        self.logger.info(f"Running scraper {scraper.handler}::{scraper.name}")

        if handler.name != scraper.handler:
            self.logger.warning(
                f"Provided handler's name ({handler.name}) doesn't match scraper handler name ({scraper.handler})"
            )

        async def _update_scraper_state(scraper_id: ScraperId, state: str) -> Scraper:
            scraper = await self._scrapers_storage.get_scraper(scraper_id)
            scraper.state = state
            return await self._scrapers_storage.update_scraper(scraper)

        context = ScraperContext(
            scraper.config,
            self.middlewares,
            scraper_state=scraper.state,
            update_scraper_state_func=_update_scraper_state,
        )
        try:
            await context.start_session()
            return await handler.run(context)
        except Exception:
            self.logger.exception(
                f"Failed to run scraper {scraper.handler}::{scraper.name}"
            )
        finally:
            await context.close()
