from typing import Any

from pydantic import BaseModel


class ScraperConfig(BaseModel):
    """Scraper configuration

    Attributes:
        params (dict[str, Any] | None): Scraper configuration that is passed to the handler. Defaults to None.
        plugins (dict[str, Any] | None): Plugins configuration that defines which plugins to use (besides global ones). Takes precedence over global plugin configuration. Defaults to None.
    """

    params: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
