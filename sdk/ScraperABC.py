from abc import ABC

from sdk.ScraperContext import ScraperContext


class ScraperABC(ABC):
    def run(self, context: ScraperContext):
        raise NotImplementedError()
