from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, Awaitable, Callable

import aiohttp
import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel
from typing_extensions import override

from sneakpeek.queue.model import TaskPriority
from sneakpeek.scheduler.model import (
    PeriodicTask,
    PeriodicTasksStorageABC,
    TaskSchedule,
)

SCRAPER_PERIODIC_TASK_HANDLER_NAME = "scraper"
EPHEMERAL_SCRAPER_TASK_HANDLER_NAME = "ephemeral_scraper"

ScraperId = str
HttpHeaders = dict[str, str]
MiddlewareConfig = Any
Response = aiohttp.ClientResponse | list[aiohttp.ClientResponse | Exception]


class ScraperConfig(BaseModel):
    #: Scraper configuration that is passed to the handler. Defaults to None.
    params: dict[str, Any] | None = None
    #: Middleware configuration that defines which middleware to use (besides global ones). Takes precedence over global middleware configuration. Defaults to None.
    middleware_config: dict[str, Any] | None = None


class Scraper(BaseModel):
    """Scraper metadata"""

    id: ScraperId  #: Scraper unique identifier
    name: str  #: Scraper name
    handler: str  #: Name of the scraper handler that implements scraping logic
    schedule: TaskSchedule  #: Scraper schedule configuration
    schedule_crontab: str | None  #: Must be defined if schedule equals to ``CRONTAB``
    config: ScraperConfig  #: Scraper configuration that is passed to the handler
    #: Default priority to enqueue scraper jobs with
    priority: TaskPriority = TaskPriority.NORMAL
    #: Scraper state (might be useful to optimise scraping, e.g. only process pages that weren't processed in the last jobs)
    state: str | None = None
    #: Timeout for the single scraper job
    timeout: timedelta | None = None


class ScraperNotFoundError(jsonrpc.BaseError):
    CODE = 5000
    MESSAGE = "Scraper not found"


class StorageIsReadOnlyError(jsonrpc.BaseError):
    CODE = 5001
    MESSAGE = "StorageIsReadOnlyError"


class UnknownScraperHandlerError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Unknown scraper handler"


class CreateScraperRequest(BaseModel):
    name: str  #: Scraper name
    handler: str  #: Name of the scraper handler that implements scraping logic
    schedule: TaskSchedule  #: Scraper schedule configuration
    schedule_crontab: str | None  #: Must be defined if schedule equals to ``CRONTAB``
    config: ScraperConfig  #: Scraper configuration that is passed to the handler
    #: Default priority to enqueue scraper jobs with
    priority: TaskPriority = TaskPriority.NORMAL
    #: Timeout for the single scraper job
    timeout_seconds: int | None = None


class ScraperStorageABC(PeriodicTasksStorageABC):
    @abstractmethod
    def is_read_only(self) -> bool:
        ...

    @abstractmethod
    async def create_scraper(self, request: CreateScraperRequest) -> Scraper:
        ...

    @abstractmethod
    async def update_scraper(self, request: Scraper) -> Scraper:
        ...

    @abstractmethod
    async def delete_scraper(self, id: ScraperId) -> Scraper:
        ...

    @abstractmethod
    async def get_scraper(self, id: ScraperId) -> Scraper:
        ...

    @abstractmethod
    async def get_scrapers(self) -> list[Scraper]:
        ...

    def _convert_scraper_to_periodic_task(self, scraper: Scraper) -> PeriodicTask:
        return PeriodicTask(
            id=scraper.id,
            name=scraper.id,
            handler=SCRAPER_PERIODIC_TASK_HANDLER_NAME,
            priority=scraper.priority,
            schedule=scraper.schedule,
            schedule_crontab=scraper.schedule_crontab,
            timeout=timedelta(seconds=scraper.timeout) if scraper.timeout else None,
            payload="",
        )

    @override
    async def get_periodic_tasks(self) -> list[PeriodicTask]:
        return [
            self._convert_scraper_to_periodic_task(scraper)
            for scraper in await self.get_scrapers()
        ]


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


class Middleware(ABC):
    """Abstract class for the middleware which is called before each request and response"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the middleware"""
        ...

    @abstractmethod
    async def on_request(
        self,
        request: Request,
        config: MiddlewareConfig | None = None,
    ) -> Request:
        """
        Function that is called on each (HTTP) request before its dispatched.

        Args:
            request (Request): Request metadata
            config (Any | None, optional): Middleware configuration. Defaults to None.

        Returns:
            Request: Request metadata
        """
        return request

    @abstractmethod
    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: MiddlewareConfig | None = None,
    ) -> aiohttp.ClientResponse:
        """
        Function that is called on each (HTTP) response before its result returned to the caller.

        Args:
            request (Request): Request metadata
            response (aiohttp.ClientResponse): HTTP Response
            config (Any | None, optional): Middleware configuration. Defaults to None.

        Returns:
            aiohttp.ClientResponse: HTTP Response
        """
        return response


class ScraperContextABC(ABC):
    """
    Scraper context - helper class that implements basic HTTP client which logic can be extended by
    middleware that can preprocess request (e.g. Rate Limiter) and postprocess response (e.g. Response logger).
    """

    async def start_session(self) -> None:
        self._session = aiohttp.ClientSession()
        await self._session.__aenter__()
        return self

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        return self

    @abstractmethod
    async def on_request(self, request: Request) -> Request:
        return request

    @abstractmethod
    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
    ) -> aiohttp.ClientResponse:
        return response

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

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

    @abstractmethod
    async def update_scraper_state(self, state: str) -> Scraper:
        """Update scraper state

        Args:
            state (str): State to persist

        Returns:
            Scraper: Updated scraper metadata
        """
        ...


class ScraperHandler(ABC):
    """Abstract class that scraper logic handler must implement"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the handler"""
        ...

    @abstractmethod
    async def run(self, context: ScraperContextABC) -> str:
        """Execute scraper logic

        Args:
            context (ScraperContext): Scraper context

        Returns:
            str: scraper result that will be persisted in the storage (should be relatively small information to give sense on job result)
        """
        ...


class ScraperRunnerABC(ABC):
    @abstractmethod
    async def run(self, handler: ScraperHandler, scraper: Scraper) -> str:
        """
        Args:
            handler (ScraperHandler): Scraper logic implementation
            scraper (Scraper): Scraper metadata
        """
        ...

    @abstractmethod
    async def run_ephemeral(
        self,
        handler: ScraperHandler,
        config: ScraperConfig | None = None,
        state: str | None = None,
    ) -> str | None:
        ...
