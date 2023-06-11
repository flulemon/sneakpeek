import logging
from uuid import uuid4

from sneakpeek.logging import configure_logging
from sneakpeek.metrics import count_invocations
from sneakpeek.scheduler.models import TaskSchedule
from sneakpeek.scraper.context import ScraperContext
from sneakpeek.scraper.in_memory_storage import InMemoryScraperStorage
from sneakpeek.scraper.models import (
    Middleware,
    Scraper,
    ScraperConfig,
    ScraperHandler,
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

    @staticmethod
    async def debug_handler(
        handler: ScraperHandler,
        config: ScraperConfig | None = None,
        state: str | None = None,
        middlewares: list[Middleware] | None = None,
        log_level: int = logging.DEBUG,
    ):
        configure_logging(log_level)
        scraper = Scraper(
            id=str(uuid4()),
            name="test_handler",
            handler=handler.name,
            schedule=TaskSchedule.INACTIVE,
            config=config,
            state=state,
        )
        return await ScraperRunner(
            InMemoryScraperStorage([scraper]),
            middlewares=middlewares,
        ).run(handler, scraper)

    @count_invocations(subsystem="scraper_runner")
    async def run(self, handler: ScraperHandler, scraper: Scraper) -> str:
        self.logger.info(f"Running scraper {scraper.handler}::{scraper.name}")

        if handler.name != scraper.handler:
            self.logger.warning(
                f"Provided handler's name ({handler.name}) doesn't match scraper handler name ({scraper.handler})"
            )

        async def _update_scraper_state(state: str) -> Scraper:
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
