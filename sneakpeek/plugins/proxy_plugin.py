from typing import Any

from aiohttp import BasicAuth
from fake_useragent import UserAgent
from pydantic import BaseModel
from yarl import URL

from sneakpeek.plugins.utils import parse_config_from_obj
from sneakpeek.scraper_context import BeforeRequestPlugin, Request


class ProxyPluginConfig(BaseModel):
    proxy: str | URL | None = None
    proxy_auth: BasicAuth | None = None


class ProxyPlugin(BeforeRequestPlugin):
    def __init__(self, default_config: ProxyPluginConfig | None = None) -> None:
        self._default_config = default_config or ProxyPluginConfig()
        self._user_agents = UserAgent(
            use_external_data=self._default_config.use_external_data,
            browsers=self._default_config.browsers,
        )

    @property
    def name(self) -> str:
        return "proxy"

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            ProxyPluginConfig,
            self._default_config,
        )
        if not request.kwargs:
            request.kwargs = {}
        if config.proxy:
            request.kwargs["proxy"] = config.proxy
        if config.proxy_auth:
            request.kwargs["proxy_auth"] = config.proxy_auth
        return request
