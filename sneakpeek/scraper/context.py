import asyncio
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import uuid4

import aiohttp
from typing_extensions import override

from sneakpeek.scraper.model import (
    HttpHeaders,
    HttpMethod,
    Middleware,
    Request,
    Response,
    Scraper,
    ScraperConfig,
    ScraperContextABC,
)


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


class ScraperContext(ScraperContextABC):
    """
    Scraper context - helper class that implements basic HTTP client which logic can be extended by
    plugins that can preprocess request (e.g. Rate Limiter) and postprocess response (e.g. Response logger).
    """

    def __init__(
        self,
        config: ScraperConfig,
        middlewares: list[Middleware] | None = None,
        scraper_state: str | None = None,
        update_scraper_state_func: Callable | None = None,
    ) -> None:
        """
        Args:
            config (ScraperConfig): Scraper configuration
            middleware (list[Middleware] | None, optional): List of available middleware. Defaults to None.
            scraper_state (str | None, optional): Scraper state. Defaults to None.
            update_scraper_state_func (Callable | None, optional): Function that update scraper state. Defaults to None.
        """
        self.params = config.params
        self.state = scraper_state
        self.update_scraper_state_func = update_scraper_state_func
        self.logger = logging.getLogger(__name__)
        self.middleware_config = config.middleware_config or {}
        self.session: aiohttp.ClientSession | None = None
        self.middlewares = middlewares or []
        self._init_middleware(middlewares)

    def _init_middleware(self, middlewares: list[Middleware] | None = None) -> None:
        for middleware in middlewares or []:
            if not middleware.name.isidentifier():
                raise ValueError(
                    "Plugin name must be a Python identifier. "
                    f"Plugin {middleware.__class__} has invalid name: {middleware.name}"
                )
            setattr(self, middleware.name, middleware)

    async def start_session(self) -> None:
        self._session = aiohttp.ClientSession()
        await self._session.__aenter__()
        return self

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        return self

    @override
    async def on_request(self, request: Request) -> Request:
        for middleware in self.middlewares:
            request = await middleware.on_request(
                request,
                self.middleware_config.get(middleware.name),
            )
        return request

    @override
    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
    ) -> aiohttp.ClientResponse:
        for middleware in self.middlewares:
            response = await middleware.on_response(
                request,
                response,
                self.middleware_config.get(middleware.name),
            )
        return response

    async def _single_request(self, request: Request) -> aiohttp.ClientResponse:
        request = await self.on_request(request)
        response = await getattr(self._session, request.method)(
            request.url,
            headers=request.headers,
            **(request.kwargs or {}),
        )
        response = await self.on_response(request, response)
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

    async def update_scraper_state(self, state: str) -> Scraper:
        if not self._update_scraper_state_func:
            self._logger.warning(
                "Tried to update scraper state, but the function to do it is not set"
            )
            return
        return await self._update_scraper_state_func(state)
