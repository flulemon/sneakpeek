import asyncio
import itertools
import json
import logging
import os
import pathlib
from asyncio import AbstractEventLoop
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock
from traceback import format_exc
from typing import Any, List

from sneakpeek.session_loggers.base import LogLine, SessionLogger, get_fields_to_log

MAX_BUFFER_AGE = timedelta(seconds=5)


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class FileLoggerHandler(SessionLogger):
    def __init__(
        self,
        directory: str,
        loop: AbstractEventLoop | None = None,
        max_buffer_size: int = 10,
        max_buffer_age: timedelta = MAX_BUFFER_AGE,
        max_log_files_to_keep: int = 1000,
    ) -> None:
        super().__init__()
        self.dir = directory
        self.loop = loop or asyncio.get_event_loop()
        self.max_buffer_size = max_buffer_size
        self.max_buffer_age = max_buffer_age
        self.buffer: dict[str, Any] = defaultdict(list)
        self.last_flush = datetime.min
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.max_log_files_to_keep = max_log_files_to_keep
        self._lock = Lock()

    def _cleanup(self):
        if not os.path.exists(self.dir):
            return
        with self._lock:
            with os.scandir(self.dir) as it:
                log_files = sorted(
                    [entry for entry in it if entry.is_file()],
                    key=lambda x: x.stat().st_mtime,
                )
            for file in log_files[: -self.max_log_files_to_keep]:
                os.remove(file.path)

    def flush(self):
        """
        Flushes the stream.
        """
        with self.lock:
            self._cleanup()
            try:
                pathlib.Path(self.dir).mkdir(parents=True, exist_ok=True)
                for group, messages in self.buffer.items():
                    with open(
                        os.path.join(self.dir, f"task_{group}.log"), mode="a"
                    ) as f:
                        f.writelines(
                            [f"{json.dumps(m, cls=Encoder)}\n" for m in messages]
                        )
            except Exception:
                print(format_exc())
            self.buffer.clear()

    def emit(self, record: logging.LogRecord) -> None:
        if not getattr(record, "task_id"):
            return

        self.buffer[record.task_id].append(get_fields_to_log(record))
        with self._lock:
            if (
                len(self.buffer) > self.max_buffer_size
                or datetime.utcnow() - self.last_flush > self.max_buffer_age
            ):
                self.loop.run_in_executor(self.executor, self.flush)

    async def read(
        self,
        task_id: str,
        last_log_line_id: str | None = None,
        max_lines: int = 100,
    ) -> List[dict[str, Any]]:
        path = os.path.join(self.dir, f"task_{task_id}.log")
        if not os.path.exists(path):
            return []
        last_log_line_id = int(last_log_line_id) if last_log_line_id else 0

        with open(path, "r") as f:
            return [
                LogLine(
                    id=last_log_line_id + line_num + 1,
                    data=json.loads(line),
                )
                for line_num, line in enumerate(
                    itertools.islice(
                        f,
                        last_log_line_id,
                        last_log_line_id + max_lines,
                    )
                )
            ]
