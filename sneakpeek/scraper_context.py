import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import aiohttp

from sneakpeek.lib.errors import (
    ScraperRunPingFinishedError,
    ScraperRunPingNotStartedError,
)
from sneakpeek.scraper_config import ScraperConfig

HttpHeaders = dict[str, str]
PluginConfig = Any


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    HEAD = "head"
    PUT = "PUT"
    DELETE = "delete"
    OPTIONS = "options"


@dataclass
class Request:
    method: HttpMethod
    url: str
    headers: HttpHeaders | None = None
    kwargs: dict[str, Any] | None = None


class BeforeRequestPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def before_request(
        self,
        request: Request,
        config: Any | None = None,
    ) -> Request:
        ...


class AfterResponsePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None = None,
    ) -> aiohttp.ClientResponse:
        ...


Plugin = BeforeRequestPlugin | AfterResponsePlugin


class ScraperContext:
    def __init__(
        self,
        config: ScraperConfig,
        plugins: list[Plugin] | None = None,
        ping_session_func: Callable | None = None,
    ) -> None:
        self.params = config.params
        self.ping_session_func = ping_session_func
        self._logger = logging.getLogger(__name__)
        self._plugins_configs = config.plugins or {}
        self._session: aiohttp.ClientSession | None = None
        self._before_request_plugins = []
        self._after_response_plugins = []
        self._init_plugins(plugins)

    def _init_plugins(self, plugins: list[Plugin] | None = None) -> None:
        for plugin in plugins or []:
            if not plugin.name.isidentifier:
                raise ValueError(
                    "Plugin name must be a Python identifier. "
                    f"Plugin {plugin.__class__} has invalid name: {plugin.name}"
                )
            setattr(self, plugin.name, plugin)
            if isinstance(plugin, BeforeRequestPlugin):
                self._before_request_plugins.append(plugin)
            if isinstance(plugin, AfterResponsePlugin):
                self._after_response_plugins.append(plugin)

    async def start_session(self) -> None:
        self._session = aiohttp.ClientSession()
        await self._session.__aenter__()
        return self

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        return self

    async def _before_request(self, request: Request) -> Request:
        for plugin in self._before_request_plugins:
            request = await plugin.before_request(
                request,
                self._plugins_configs.get(plugin.name),
            )
        return request

    async def _after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
    ) -> aiohttp.ClientResponse:
        for plugin in self._after_response_plugins:
            response = await plugin.after_response(
                request,
                response,
                self._plugins_configs.get(plugin.name),
            )
        return response

    async def _request(self, request: Request) -> aiohttp.ClientResponse:
        await self.ping_session()
        request = await self._before_request(request)
        response = await getattr(self._session, request.method)(
            request.url,
            headers=request.headers,
            **(request.kwargs or {}),
        )
        response = await self._after_response(request, response)
        await self.ping_session()
        return response

    async def ping_session(self) -> None:
        if not self.ping_session_func:
            self._logger.warning(
                "Tried to ping scraper run, but the function to ping session is None"
            )
            return
        try:
            await self.ping_session_func()
        except ScraperRunPingNotStartedError as e:
            self._logger.error(
                f"Failed to ping PENDING scraper run because due to some infra error: {e}"
            )
            raise
        except ScraperRunPingFinishedError as e:
            self._logger.error(
                f"Failed to ping scraper run because seems like it's been killed: {e}"
            )
            raise
        except Exception as e:
            self._logger.error(f"Failed to ping scraper run: {e}")

    async def get(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.GET,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    async def post(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.POST,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    async def head(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.HEAD,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    async def delete(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.DELETE,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    async def put(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.PUT,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    async def options(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(
            Request(
                method=HttpMethod.OPTIONS,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )
