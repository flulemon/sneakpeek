import logging
from traceback import format_exc
from typing import Any, Coroutine, Type, TypeVar

from aiohttp import ClientResponse
from pydantic import BaseModel
from typing_extensions import override

from sneakpeek.scraper.model import Middleware, MiddlewareConfig, Request

logger = logging.getLogger(__name__)

_TBaseModel = TypeVar("_TBaseModel", bound=BaseModel)


def parse_config_from_obj(
    config: Any | None,
    plugin_name: str,
    config_type: Type[_TBaseModel],
    default_config: _TBaseModel,
) -> _TBaseModel:
    if not config:
        return default_config
    try:
        return config_type.parse_obj(config)
    except Exception as e:
        logger.warn(f"Failed to parse config for plugin '{plugin_name}': {e}")
        logger.debug(f"Traceback: {format_exc()}")
    return default_config


class BaseMiddleware(Middleware):
    @property
    def name(self) -> str:
        return "proxy"

    @override
    async def on_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        return request

    async def on_response(
        self,
        request: Request,
        response: ClientResponse,
        config: MiddlewareConfig | None = None,
    ) -> Coroutine[Any, Any, ClientResponse]:
        return response
