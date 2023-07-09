import asyncio
import logging
from uuid import uuid4

from sneakpeek.metrics import count_invocations
from sneakpeek.scheduler.model import TaskSchedule
from sneakpeek.scraper.context import ScraperContext
from sneakpeek.scraper.in_memory_storage import InMemoryScraperStorage
from sneakpeek.scraper.model import (
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
        loop: asyncio.AbstractEventLoop | None = None,
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
    ) -> str:
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
    async def run_ephemeral(
        self,
        handler: ScraperHandler,
        config: ScraperConfig | None = None,
        state: str | None = None,
    ) -> str | None:
        self.logger.info(f"Running ephemeral scraper with {handler.name}")

        context = ScraperContext(
            config,
            self.middlewares,
            scraper_state=state,
        )
        try:
            await context.start_session()
            result = await handler.run(context)
            self.logger.info(
                f"Successfully executed ephemeral scraper with {handler.name}: {result}"
            )
            return result
        except Exception:
            self.logger.exception(
                f"Failed to run ephemeral scraper with {handler.name}"
            )
            raise
        finally:
            await context.close()

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
            result = await handler.run(context)
            self.logger.info(
                f"Successfully executed ephemeral scraper with {handler.name}: {result}"
            )
            return result
        except Exception:
            self.logger.exception(
                f"Failed to run scraper {scraper.handler}::{scraper.name}"
            )
            raise
        finally:
            await context.close()
