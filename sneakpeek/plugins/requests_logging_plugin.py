import logging
from traceback import format_exc
from typing import Any

import aiohttp
from pydantic import BaseModel

from sneakpeek.scraper_context import AfterResponsePlugin, BeforeRequestPlugin, Request


class RequestsLoggingPluginConfig(BaseModel):
    log_request: bool = True
    log_response: bool = True


class RequestsLoggingPlugin(BeforeRequestPlugin, AfterResponsePlugin):
    def __init__(self, config: RequestsLoggingPluginConfig | None = None) -> None:
        self._default_config = config or RequestsLoggingPluginConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "requests_logging_plugin"

    def _parse_config(self, config: Any | None) -> RequestsLoggingPluginConfig:
        if not config:
            return self._default_config
        try:
            return RequestsLoggingPluginConfig.parse_obj(config)
        except Exception as e:
            self._logger.warn(f"Failed to parse config for plugin '{self.name}': {e}")
            self._logger.debug(f"Traceback: {format_exc()}")
        return self._default_config

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = self._parse_config(config)
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
        config = self._parse_config(config)
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
