import logging
from typing import Any

import aiohttp
from pydantic import BaseModel

from sneakpeek.plugins.utils import parse_config_from_obj
from sneakpeek.scraper_context import AfterResponsePlugin, BeforeRequestPlugin, Request


class RequestsLoggingPluginConfig(BaseModel):
    log_request: bool = True
    log_response: bool = True


class RequestsLoggingPlugin(BeforeRequestPlugin, AfterResponsePlugin):
    def __init__(
        self, default_config: RequestsLoggingPluginConfig | None = None
    ) -> None:
        self._default_config = default_config or RequestsLoggingPluginConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "requests_logging"

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            RequestsLoggingPluginConfig,
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

    async def after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None,
    ) -> aiohttp.ClientResponse:
        config = parse_config_from_obj(
            config,
            self.name,
            RequestsLoggingPluginConfig,
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
