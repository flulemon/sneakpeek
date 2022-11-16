from typing import Any

from pydantic import BaseModel


class ScraperConfig(BaseModel):
    params: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
