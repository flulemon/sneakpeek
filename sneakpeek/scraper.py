from abc import ABC
from typing import Any

from sneakpeek.context import ScraperContext


class ScraperABC(ABC):
    @property
    def name(self) -> str:
        raise NotImplementedError()

    def run(self, context: ScraperContext, params: Any) -> str:
        raise NotImplementedError()
