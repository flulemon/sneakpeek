from pydantic import BaseModel


class HttpProxyConfig(BaseModel):
    host: str
    port: int


class ScraperConfig(BaseModel):
    scraper_params_json: str | None = None
    proxy: HttpProxyConfig | None = None
    user_agents: list[str] | None = None
    use_session: bool = True
