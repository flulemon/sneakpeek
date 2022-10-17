import logging
import random
from enum import Enum
from typing import Dict

import aiohttp

from sneakpeek.config import ScraperConfig

_Headers = Dict[str, str]


class _Method(str, Enum):
    GET = "get"
    POST = "post"
    HEAD = "head"
    PUT = "PUT"
    DELETE = "delete"
    OPTIONS = "options"


class ScraperContext:
    def __init__(
        self,
        scraper_id: int,
        run_id: int,
        config: ScraperConfig,
    ) -> None:
        self.config = config
        self._scraper_id = scraper_id
        self._run_id = run_id
        self._logger = logging.getLogger(__name__)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> None:
        self._session = aiohttp.ClientSession()
        await self._session.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        if self._session:
            await self._session.__aexit__(*args)
            self._session = None
        return self

    def _inject_headers(
        self,
        headers: _Headers | None = None,
    ) -> _Headers:
        headers = headers or {}
        if self.config.user_agents and "User-Agent" not in headers:
            headers["User-Agent"] = random.choice(self.config.use_session)
        return headers

    def _on_request(
        self,
        method: _Method,
        url: str,
        headers: _Headers | None = None,
        **kwargs,
    ) -> None:
        self._logger.info(
            f"{method} {url}",
            extra={
                "headers": headers,
                **kwargs,
            },
        )

    def _on_response(
        self,
        response: aiohttp.ClientResponse,
        method: _Method,
        url: str,
        headers: _Headers | None = None,
        **kwargs,
    ) -> None:
        succeeded = response.status < 400
        self._logger.log(
            level=logging.INFO if succeeded else logging.ERROR,
            msg=f"{response.status} {method} {url}",
            extra={
                "headers": headers,
                **kwargs,
            },
        )

    async def _request(
        self,
        method: _Method,
        url: str,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        self._on_request(method, url, headers, **kwargs)
        response = await getattr(self._session, method)(
            url,
            headers=headers,
            **kwargs,
        )
        self._on_response(response, method, url, headers, **kwargs)
        return response

    async def get(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.GET, url, headers, **kwargs)

    async def post(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.POST, url, headers, **kwargs)

    async def head(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.HEAD, url, headers, **kwargs)

    async def delete(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.DELETE, url, headers, **kwargs)

    async def put(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.PUT, url, headers, **kwargs)

    async def options(
        self,
        url: str,
        *,
        headers: _Headers | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._request(_Method.OPTIONS, url, headers, **kwargs)
