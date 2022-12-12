import asyncio
import logging
from asyncio import Lock
from datetime import datetime, timedelta
from enum import Enum, auto
from random import randint
from typing import Any
from urllib.parse import urlparse

from cachetools.func import ttl_cache
from pydantic import BaseModel, validator

from sneakpeek.plugins.utils import parse_config_from_obj
from sneakpeek.scraper_context import BeforeRequestPlugin, Request

DEFAULT_BUCKET_TIME_WINDOW = timedelta(minutes=1)


def rate_limited_delay_jitter() -> timedelta:
    return timedelta(milliseconds=randint(0, 500))


class _LeakyBucket:
    def __init__(
        self, size: int, time_window: timedelta = DEFAULT_BUCKET_TIME_WINDOW
    ) -> None:
        self.size = size
        self.time_window = time_window
        self.queue: list[datetime] = []
        self.lock = Lock()

    def last_used(self) -> datetime | None:
        if not self.queue:
            return None
        return self.queue[0]

    async def add(self) -> datetime | None:
        async with self.lock:
            now = datetime.utcnow()
            while self.queue and self.queue[0] <= now - self.time_window:
                self.queue.pop(0)
            if not self.size:
                raise ValueError("Queue size is 0")
            if len(self.queue) >= self.size:
                return self.queue[0] + self.time_window

            self.queue.append(now)
            return None


class RateLimitedException(Exception):
    pass


class RateLimitedStrategy(Enum):
    THROW = auto()
    WAIT = auto()


class RateLimiterPluginConfig(BaseModel):
    max_rpm: int = 60
    rate_limited_strategy: RateLimitedStrategy = RateLimitedStrategy.WAIT
    time_window: timedelta = DEFAULT_BUCKET_TIME_WINDOW

    @validator("max_rpm")
    def check_max_rpm(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"`max_rpm` must be a positive integer. Received: {v}")
        return v

    def __hash__(self):
        return hash(
            (
                self.max_rpm,
                self.rate_limited_strategy,
                self.time_window,
            )
        )


class RateLimiterPlugin(BeforeRequestPlugin):
    def __init__(self, default_config: RateLimiterPluginConfig | None = None) -> None:
        self._default_config = default_config or RateLimiterPluginConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "rate_limiter"

    def _extract_key(self, url: str) -> str:
        return urlparse(url).hostname

    @ttl_cache(maxsize=None, ttl=timedelta(minutes=5).total_seconds())
    def _get_bucket(self, key: str, config: RateLimiterPluginConfig) -> _LeakyBucket:
        return _LeakyBucket(
            size=config.max_rpm,
            time_window=config.time_window,
        )

    async def _wait_for_admission(
        self,
        url: str,
        config: RateLimiterPluginConfig,
    ) -> None:
        key = self._extract_key(url)
        bucket = self._get_bucket(key, config)
        while True:
            next_attempt_dt = await bucket.add()
            if not next_attempt_dt:
                return
            error_message = (
                f"Rate limited request to '{url}' because there were "
                f"more than {bucket.size} calls in the last {int(bucket.time_window.total_seconds())}s "
                f"to the domain {key}. "
                f"Next available call will be permitted at {next_attempt_dt}."
            )

            if config.rate_limited_strategy == RateLimitedStrategy.THROW:
                raise RateLimitedException(error_message)
            self._logger.info(error_message)
            attempt_delay = next_attempt_dt - datetime.utcnow()
            attempt_delay += rate_limited_delay_jitter()
            await asyncio.sleep(attempt_delay.total_seconds())

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            RateLimiterPluginConfig,
            self._default_config,
        )
        await self._wait_for_admission(request.url, config)
        return request
