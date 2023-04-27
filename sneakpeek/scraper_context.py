import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import aiohttp

from sneakpeek.lib.errors import (
    ScraperJobPingFinishedError,
    ScraperJobPingNotStartedError,
)
from sneakpeek.scraper_config import ScraperConfig

HttpHeaders = dict[str, str]
PluginConfig = Any


class HttpMethod(str, Enum):
    """HTTP method"""

    GET = "get"
    POST = "post"
    HEAD = "head"
    PUT = "PUT"
    DELETE = "delete"
    OPTIONS = "options"


@dataclass
class Request:
    """HTTP Request metadata"""

    method: HttpMethod
    url: str
    headers: HttpHeaders | None = None
    kwargs: dict[str, Any] | None = None


@dataclass
class RegexMatch:
    """Regex match"""

    full_match: str  #: Full regular expression match
    groups: dict[str, str]  #: Regular expression group matches


class BeforeRequestPlugin(ABC):
    """Abstract class for the plugin which is called before each request (like Middleware)"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the plugin"""
        ...

    @abstractmethod
    async def before_request(
        self,
        request: Request,
        config: Any | None = None,
    ) -> Request:
        """
        Function that is called on each (HTTP) request before its dispatched.

        Args:
            request (Request): Request metadata
            config (Any | None, optional): Plugin configuration. Defaults to None.

        Returns:
            Request: Request metadata
        """
        ...


class AfterResponsePlugin(ABC):
    """Abstract class for the plugin which is called after each request"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the plugin"""
        ...

    @abstractmethod
    async def after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None = None,
    ) -> aiohttp.ClientResponse:
        """
        Function that is called on each (HTTP) response before its result returned to the caller.

        Args:
            request (Request): Request metadata
            response (aiohttp.ClientResponse): HTTP Response
            config (Any | None, optional): Plugin configuration. Defaults to None.

        Returns:
            aiohttp.ClientResponse: HTTP Response
        """
        ...


Plugin = BeforeRequestPlugin | AfterResponsePlugin


class ScraperContext:
    """
    Scraper context - helper class that implements basic HTTP client which logic can be extended by
    plugins that can preprocess request (e.g. Rate Limiter) and postprocess response (e.g. Response logger).
    """

    def __init__(
        self,
        config: ScraperConfig,
        plugins: list[Plugin] | None = None,
        ping_session_func: Callable | None = None,
    ) -> None:
        """
        Args:
            config (ScraperConfig): Scraper configuration
            plugins (list[BeforeRequestPlugin | AfterResponsePlugin] | None, optional): List of available plugins. Defaults to None.
            ping_session_func (Callable | None, optional): Function that pings scraper job. Defaults to None.
        """
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
        """Ping scraper job, so it's not considered dead"""
        if not self.ping_session_func:
            self._logger.warning(
                "Tried to ping scraper job, but the function to ping session is None"
            )
            return
        try:
            await self.ping_session_func()
        except ScraperJobPingNotStartedError as e:
            self._logger.error(
                f"Failed to ping PENDING scraper job because due to some infra error: {e}"
            )
            raise
        except ScraperJobPingFinishedError as e:
            self._logger.error(
                f"Failed to ping scraper job because seems like it's been killed: {e}"
            )
            raise
        except Exception as e:
            self._logger.error(f"Failed to ping scraper job: {e}")

    async def get(
        self,
        url: str,
        *,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make GET request to the given URL

        Args:
            url (str): URL to send GET request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.get() for the full list of arguments
        """
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
        """Make POST request to the given URL

        Args:
            url (str): URL to send POST request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.get() for the full list of arguments
        """
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
        """Make HEAD request to the given URL

        Args:
            url (str): URL to send HEAD request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.head() for the full list of arguments
        """
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
        """Make DELETE request to the given URL

        Args:
            url (str): URL to send DELETE request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.delete() for the full list of arguments
        """
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
        """Make PUT request to the given URL

        Args:
            url (str): URL to send PUT request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.put() for the full list of arguments
        """
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
        """Make OPTIONS request to the given URL

        Args:
            url (str): URL to send OPTIONS request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.options() for the full list of arguments
        """
        return await self._request(
            Request(
                method=HttpMethod.OPTIONS,
                url=url,
                headers=headers,
                kwargs=kwargs,
            )
        )

    def regex(
        self,
        text: str,
        pattern: str,
        flags: re.RegexFlag = re.UNICODE | re.MULTILINE | re.IGNORECASE,
    ) -> list[RegexMatch]:
        """Find matches in the text using regular expression

        Args:
            text (str): Text to search in
            pattern (str): Regular expression
            flags (re.RegexFlag, optional): Regular expression flags. Defaults to re.UNICODE | re.MULTILINE | re.IGNORECASE.

        Returns:
            list[RegexMatch]: Matches found in the text
        """
        return [
            RegexMatch(full_match=match.group(0), groups=match.groupdict())
            for match in re.finditer(pattern, text, flags)
        ]
