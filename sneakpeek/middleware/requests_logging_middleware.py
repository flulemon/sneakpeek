import logging
from typing import Any

import aiohttp
from pydantic import BaseModel
from typing_extensions import override

from sneakpeek.middleware.base import parse_config_from_obj
from sneakpeek.scraper.model import Middleware, Request


class RequestsLoggingMiddlewareConfig(BaseModel):
    """Requests logging middleware config"""

    log_request: bool = True  #: Whether to log request being made
    log_response: bool = True  #: Whether to log response being made


class RequestsLoggingMiddleware(Middleware):
    """Requests logging middleware logs all requests being made and received responses."""

    def __init__(
        self, default_config: RequestsLoggingMiddlewareConfig | None = None
    ) -> None:
        self._default_config = default_config or RequestsLoggingMiddlewareConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "requests_logging"

    @override
    async def on_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            RequestsLoggingMiddlewareConfig,
            self._default_config,
        )
        if config.log_request:
            self._logger.info(
                f"{request.method.upper()} {request.url}",
                extra={
                    "headers": request.headers,
                    "kwargs": request.kwargs,
                },
            )
        return request

    @override
    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None,
    ) -> aiohttp.ClientResponse:
        config = parse_config_from_obj(
            config,
            self.name,
            RequestsLoggingMiddlewareConfig,
            self._default_config,
        )
        if config.log_response:
            response_body = await response.text()
            self._logger.info(
                f"{request.method.upper()} {request.url} - {response.status} ",
                extra={
                    "headers": request.headers,
                    "kwargs": request.kwargs,
                    "response": {response_body},
                },
            )
        return response
