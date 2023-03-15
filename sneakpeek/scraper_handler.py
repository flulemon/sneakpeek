from abc import ABC, abstractmethod

from sneakpeek.scraper_context import ScraperContext


class ScraperHandler(ABC):
    """Abstract class that scraper logic handler must implement"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the handler"""
        ...

    @abstractmethod
    async def run(self, context: ScraperContext) -> str:
        """Execute scraper logic

        Args:
            context (ScraperContext): Scraper context

        Returns:
            str: scraper result that will be persisted in the storage (should be relatively small information to give sense on job result)
        """
        ...
