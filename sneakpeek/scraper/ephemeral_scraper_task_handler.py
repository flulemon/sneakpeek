from pydantic import BaseModel

from sneakpeek.queue.model import Task, TaskHandlerABC
from sneakpeek.scraper.model import (
    EPHEMERAL_SCRAPER_TASK_HANDLER_NAME,
    ScraperConfig,
    ScraperHandler,
    ScraperRunnerABC,
    UnknownScraperHandlerError,
)


class EphemeralScraperTask(BaseModel):
    scraper_handler: str
    scraper_config: ScraperConfig
    scraper_state: str | None = None


class EphemeralScraperTaskHandler(TaskHandlerABC):
    def __init__(
        self,
        scraper_handlers: list[ScraperHandler],
        runner: ScraperRunnerABC,
    ) -> None:
        self.scraper_handlers = {handler.name: handler for handler in scraper_handlers}
        self.runner = runner

    def name(self) -> int:
        return EPHEMERAL_SCRAPER_TASK_HANDLER_NAME

    async def process(self, task: Task) -> str:
        config = EphemeralScraperTask.parse_raw(task.payload)
        handler = self._get_handler(config.scraper_handler)
        return await self.runner.run_ephemeral(
            handler,
            config.scraper_config,
            config.scraper_state,
        )

    def _get_handler(self, scraper_handler: str) -> ScraperHandler:
        if scraper_handler not in self.scraper_handlers:
            raise UnknownScraperHandlerError(
                f"Unknown scraper handler '{scraper_handler}'"
            )
        return self.scraper_handlers[scraper_handler]
