import logging
from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel

FIELDS_TO_LOG = [
    "levelname",
    "msg",
    "filename",
    "lineno",
    "name",
    "funcName",
    "task_id",
    "task_name",
    "task_handler",
    "asctime",
    "headers",
    "kwargs",
    "request",
    "response",
]


def get_fields_to_log(record: logging.LogRecord) -> dict[str, Any]:
    return {
        field: value
        for field in FIELDS_TO_LOG
        if (value := getattr(record, field, None)) is not None
    }


class LogLine(BaseModel):
    id: str
    data: dict[str, Any]


class SessionLogger(ABC, logging.Handler):
    @abstractmethod
    async def read(
        self,
        task_id: str,
        last_log_line_id: str | None = None,
        max_lines: int = 100,
    ) -> List[LogLine]:
        ...
