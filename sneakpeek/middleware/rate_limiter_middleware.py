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

from sneakpeek.middleware.base import BaseMiddleware, parse_config_from_obj
from sneakpeek.scraper.model import Request

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
    """Request is rate limited because too many requests were made to the host"""

    pass


class RateLimitedStrategy(Enum):
    """What to do if the request is rate limited"""

    THROW = auto()  #: Throw an exception
    WAIT = auto()  #: Wait until request is no longer rate limited


class RateLimiterMiddlewareConfig(BaseModel):
    """Rate limiter middleware configuration"""

    #: Maximum number of allowed requests per host within time window
    max_requests: int = 60
    #: What to do if the request is rate limited
    rate_limited_strategy: RateLimitedStrategy = RateLimitedStrategy.WAIT
    #: Time window to aggregate requests
    time_window: timedelta = DEFAULT_BUCKET_TIME_WINDOW

    @validator("max_requests")
    def check_max_requests(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(
                f"`max_requests` must be a positive integer. Received: {v}"
            )
        return v

    def __hash__(self):
        return hash(
            (
                self.max_requests,
                self.rate_limited_strategy,
                self.time_window,
            )
        )


class RateLimiterMiddleware(BaseMiddleware):
    """
    Rate limiter implements `leaky bucket algorithm <https://en.wikipedia.org/wiki/Leaky_bucket>`_
    to limit number of requests made to the hosts. If the request is rate limited it can either
    raise an exception or wait until the request won't be limited anymore.
    """

    def __init__(
        self, default_config: RateLimiterMiddlewareConfig | None = None
    ) -> None:
        self._default_config = default_config or RateLimiterMiddlewareConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "rate_limiter"

    def _extract_key(self, url: str) -> str:
        return urlparse(url).hostname

    @ttl_cache(maxsize=None, ttl=timedelta(minutes=5).total_seconds())
    def _get_bucket(
        self, key: str, config: RateLimiterMiddlewareConfig
    ) -> _LeakyBucket:
        return _LeakyBucket(
            size=config.max_requests,
            time_window=config.time_window,
        )

    async def _wait_for_admission(
        self,
        url: str,
        config: RateLimiterMiddlewareConfig,
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

    async def on_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            RateLimiterMiddlewareConfig,
            self._default_config,
        )
        await self._wait_for_admission(request.url, config)
        return request
