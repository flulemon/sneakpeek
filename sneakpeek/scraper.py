from abc import ABC

from sneakpeek.context import ScraperContext


class ScraperABC(ABC):
    @property
    def name(self) -> str:
        raise NotImplementedError()

    async def run(self, context: ScraperContext) -> str:
        raise NotImplementedError()
