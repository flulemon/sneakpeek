from typing import Any, List

from pydantic import BaseModel


class HttpProxyConfig(BaseModel):
    host: str
    port: int


class ScraperBaseParams(BaseModel):
    proxy: HttpProxyConfig | None
    user_agents: List[str] | None
    use_session: bool = True


class ScraperConfig(BaseModel):
    scraper_params: Any | None = None
    base_params: ScraperBaseParams | None = None
