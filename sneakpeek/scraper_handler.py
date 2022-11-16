from abc import ABC, abstractmethod

from sneakpeek.scraper_context import ScraperContext


class ScraperHandler(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def run(self, context: ScraperContext) -> str:
        ...
