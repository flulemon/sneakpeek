import logging
from asyncio import AbstractEventLoop
from copy import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from redis.asyncio import Redis

from sneakpeek.session_loggers.base import SessionLogger, get_fields_to_log

MAX_BUFFER_AGE = timedelta(seconds=5)


@dataclass
class _LogRecord:
    task_id: str
    data: Any


class RedisLoggerHandler(SessionLogger):
    def __init__(
        self,
        redis: Redis,
        loop: AbstractEventLoop | None = None,
        max_buffer_size: int = 10,
        max_buffer_age: timedelta = MAX_BUFFER_AGE,
    ) -> None:
        super().__init__()
        self.redis = redis
        self.loop = loop
        self.max_buffer_size = max_buffer_size
        self.max_buffer_age = max_buffer_age
        self.buffer: list[_LogRecord] = []
        self.last_flush = datetime.min

    async def _write_to_log(self, messages: list[_LogRecord]) -> None:
        for message in messages:
            await self.redis.xadd(name=message.task_id, fields=message.data)

    def flush(self):
        """
        Flushes the stream.
        """
        if not self.buffer:
            return
        if (
            len(self.buffer) < self.max_buffer_size
            and datetime.utcnow() - self.last_flush < self.max_buffer_age
        ):
            return
        self.acquire()
        try:
            self.loop.create_task(self._write_to_log, copy(self.buffer))
        finally:
            self.buffer.clear()
            self.release()

    def emit(self, record: logging.LogRecord) -> None:
        if not getattr(record, "task_id"):
            return

        self.buffer.append(
            _LogRecord(
                task_id=record.task_id,
                data=get_fields_to_log(record),
            )
        )
        self.flush()
