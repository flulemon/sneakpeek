import logging
from traceback import format_exc
from typing import Any, Type, TypeVar

from pydantic import BaseModel

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
