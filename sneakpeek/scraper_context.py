import asyncio
import logging
import os
import re
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable
from uuid import uuid4

import aiohttp

from sneakpeek.models import Scraper
from sneakpeek.scraper_config import ScraperConfig

HttpHeaders = dict[str, str]
PluginConfig = Any


class HttpMethod(str, Enum):
    """HTTP method"""

    GET = "get"
    POST = "post"
    HEAD = "head"
    PUT = "put"
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
class _BatchRequest:
    """HTTP Batch request metadata"""

    method: HttpMethod
    urls: list[str]
    headers: HttpHeaders | None = None
    kwargs: dict[str, Any] | None = None

    def to_single_requests(self) -> list[Request]:
        return [
            Request(
                method=self.method,
                url=url,
                headers=self.headers,
                kwargs=self.kwargs,
            )
            for url in self.urls
        ]


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
Response = aiohttp.ClientResponse | list[aiohttp.ClientResponse | Exception]


class ScraperContext:
    """
    Scraper context - helper class that implements basic HTTP client which logic can be extended by
    plugins that can preprocess request (e.g. Rate Limiter) and postprocess response (e.g. Response logger).
    """

    def __init__(
        self,
        config: ScraperConfig,
        plugins: list[Plugin] | None = None,
        scraper_state: str | None = None,
        update_scraper_state_func: Callable | None = None,
    ) -> None:
        """
        Args:
            config (ScraperConfig): Scraper configuration
            plugins (list[BeforeRequestPlugin | AfterResponsePlugin] | None, optional): List of available plugins. Defaults to None.
            scraper_state (str | None, optional): Scraper state. Defaults to None.
            update_scraper_state_func (Callable | None, optional): Function that update scraper state. Defaults to None.
        """
        self.params = config.params
        self.state = scraper_state
        self._update_scraper_state_func = update_scraper_state_func
        self._logger = logging.getLogger(__name__)
        self._plugins_configs = config.plugins or {}
        self._session: aiohttp.ClientSession | None = None
        self._before_request_plugins = []
        self._after_response_plugins = []
        self._init_plugins(plugins)

    def _init_plugins(self, plugins: list[Plugin] | None = None) -> None:
        for plugin in plugins or []:
            if not plugin.name.isidentifier():
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

    async def _single_request(self, request: Request) -> aiohttp.ClientResponse:
        request = await self._before_request(request)
        response = await getattr(self._session, request.method)(
            request.url,
            headers=request.headers,
            **(request.kwargs or {}),
        )
        response = await self._after_response(request, response)
        return response

    async def _request(
        self,
        request: _BatchRequest,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
    ) -> Response:
        single_requests = request.to_single_requests()
        if len(single_requests) == 1:
            return await self._single_request(single_requests[0])

        semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency > 0 else None

        async def process_request(request: Request):
            if semaphore:
                async with semaphore:
                    return await self._single_request(request)
            return await self._single_request(request)

        return await asyncio.gather(
            *[process_request(request) for request in single_requests],
            return_exceptions=return_exceptions,
        )

    async def request(
        self,
        method: HttpMethod,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Perform HTTP request to the given URL(s)

        Args:
            method (HttpMethod): HTTP request method to perform
            url (str | list[str]): URL(s) to send HTTP request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.request() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self._request(
            _BatchRequest(
                method=method,
                urls=url if isinstance(url, list) else [url],
                headers=headers,
                kwargs=kwargs,
            ),
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
        )

    async def download_file(
        self,
        method: HttpMethod,
        url: str,
        *,
        file_path: str | None = None,
        file_process_fn: Callable[[str], Awaitable[Any]] | None = None,
        headers: HttpHeaders | None = None,
        **kwargs,
    ) -> str | Any:
        """Perform HTTP request and save it to the specified file

        Args:
            method (HttpMethod): HTTP request method to perform
            url (str): URL to send HTTP request to
            file_path (str, optional): Path of the file to save request to. If not specified temporary file name will be generated. Defaults to None.
            file_process_fn (Callable[[str], Any], optional): Function to process the file. If specified then function will be applied to the file and its result will be returned, the file will be removed after the function call. Defaults to None.
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            **kwargs: See aiohttp.request() for the full list of arguments

        Returns:
            str | Any: File path if file process function is not defined or file process function result otherwise
        """
        if not file_path:
            file_path = os.path.join(tempfile.mkdtemp(), str(uuid4()))
        response = await self.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs,
        )
        contents = await response.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        if not file_process_fn:
            return file_path
        result = await file_process_fn(file_path)
        os.remove(file_path)
        return result

    async def download_files(
        self,
        method: HttpMethod,
        urls: list[str],
        *,
        file_paths: list[str] | None = None,
        file_process_fn: Callable[[str], Awaitable[Any]] | None = None,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> list[str | Any | Exception]:
        """Perform HTTP requests and save them to the specified files

        Args:
            method (HttpMethod): HTTP request method to perform
            urls (list[str]): URLs to send HTTP request to
            file_paths (list[str], optional): Path of the files to save requests to. If not specified temporary file names will be generated. Defaults to None.
            file_process_fn (Callable[[str], Any], optional): Function to process the file. If specified then function will be applied to the file and its result will be returned, the file will be removed after the function call. Defaults to None.
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.request() for the full list of arguments

        Returns:
            list[str | Any | Exception]: For each URL: file path if file process function is not defined or file process function result otherwise
        """
        if file_paths:
            if len(file_paths) != len(urls):
                raise ValueError(
                    f"Expected to have 1 file path per 1 URL, only have {len(file_paths)} for {len(urls)} URLs"
                )

        semaphore = asyncio.Semaphore(
            max_concurrency if max_concurrency > 0 else sys.maxsize
        )

        async def process_request(url: str, file_path: str):
            async with semaphore:
                return await self.download_file(
                    method,
                    url,
                    file_path=file_path,
                    file_process_fn=file_process_fn,
                    headers=headers,
                    **kwargs,
                )

        return await asyncio.gather(
            *[
                process_request(url, file_path)
                for url, file_path in zip(urls, file_paths)
            ],
            return_exceptions=return_exceptions,
        )

    async def get(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make GET request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send GET request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.get() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.GET,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
        )

    async def post(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make POST request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send POST request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.post() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.POST,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
        )

    async def head(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make HEAD request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send HEAD request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.head() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.HEAD,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
        )

    async def delete(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make DELETE request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send DELETE request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.delete() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.DELETE,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
        )

    async def put(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make PUT request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send PUT request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.put() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.PUT,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
        )

    async def options(
        self,
        url: str | list[str],
        *,
        headers: HttpHeaders | None = None,
        max_concurrency: int = 0,
        return_exceptions: bool = False,
        **kwargs,
    ) -> Response:
        """Make OPTIONS request to the given URL(s)

        Args:
            url (str | list[str]): URL(s) to send OPTIONS request to
            headers (HttpHeaders | None, optional): HTTP headers. Defaults to None.
            max_concurrency (int, optional): Maximum number of concurrent requests. If set to 0 no limit is applied. Defaults to 0.
            return_exceptions (bool, optional): Whether to return exceptions instead of raising if there are multiple URLs provided. Defaults to False,
            **kwargs: See aiohttp.options() for the full list of arguments

        Returns:
            Response: HTTP response(s)
        """
        return await self.request(
            HttpMethod.OPTIONS,
            url,
            headers=headers,
            max_concurrency=max_concurrency,
            return_exceptions=return_exceptions,
            **kwargs,
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

    async def update_scraper_state(self, state: str) -> Scraper:
        """Update scraper state

        Args:
            state (str): State to persist

        Returns:
            Scraper: Updated scraper metadata
        """
        if not self._update_scraper_state_func:
            self._logger.warning(
                "Tried to update scraper state, but the function to do it is not set"
            )
            return
        return await self._update_scraper_state_func(state)
