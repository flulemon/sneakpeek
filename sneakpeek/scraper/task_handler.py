from sneakpeek.queue.model import Task, TaskHandlerABC
from sneakpeek.scraper.models import (
    SCRAPER_PERIODIC_TASK_HANDLER_NAME,
    Scraper,
    ScraperHandler,
    ScraperRunnerABC,
    ScraperStorageABC,
    ScraperTaskPayload,
    UnknownScraperHandlerError,
)


class ScraperTaskHandler(TaskHandlerABC):
    def __init__(
        self,
        scraper_handlers: list[ScraperHandler],
        runner: ScraperRunnerABC,
        storage: ScraperStorageABC,
    ) -> None:
        self.scraper_handlers = {handler.name: handler for handler in scraper_handlers}
        self.runner = runner
        self.storage = storage

    def name(self) -> int:
        return SCRAPER_PERIODIC_TASK_HANDLER_NAME

    async def process(self, task: Task) -> str:
        payload = ScraperTaskPayload.parse_raw(task.payload)
        scraper = await self.storage.get_scraper(payload.id)
        handler = self._get_handler(scraper)
        return await self.runner.run(handler, scraper)

    def _get_handler(self, scraper: Scraper) -> ScraperHandler:
        if scraper.handler not in self.scraper_handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{scraper.handler}'"
            )
        return self.scraper_handlers[scraper.handler]
