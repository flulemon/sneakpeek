from typing import Any

from aiohttp import BasicAuth
from fake_useragent import UserAgent
from pydantic import BaseModel
from typing_extensions import override
from yarl import URL

from sneakpeek.middleware.base import BaseMiddleware, parse_config_from_obj
from sneakpeek.scraper.model import Request


class ProxyMiddlewareConfig(BaseModel):
    """Proxy middleware config"""

    proxy: str | URL | None = None  #: Proxy URL
    proxy_auth: BasicAuth | None = None  #: Proxy authentication info to use

    class Config:
        arbitrary_types_allowed = True


class ProxyMiddleware(BaseMiddleware):
    """Proxy middleware automatically sets proxy arguments for all HTTP requests."""

    def __init__(self, default_config: ProxyMiddlewareConfig | None = None) -> None:
        self._default_config = default_config or ProxyMiddlewareConfig()
        self._user_agents = UserAgent(
            use_external_data=self._default_config.use_external_data,
            browsers=self._default_config.browsers,
        )

    @property
    def name(self) -> str:
        return "proxy"

    @override
    async def on_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            ProxyMiddlewareConfig,
            self._default_config,
        )
        if not request.kwargs:
            request.kwargs = {}
        if config.proxy:
            request.kwargs["proxy"] = config.proxy
        if config.proxy_auth:
            request.kwargs["proxy_auth"] = config.proxy_auth
        return request
