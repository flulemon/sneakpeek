import logging
import sys
from datetime import timedelta
from enum import Enum, auto
from traceback import format_exc
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from cachetools import TTLCache
from pydantic import BaseModel

from sneakpeek.plugins.utils import parse_config_from_obj
from sneakpeek.scraper_context import BeforeRequestPlugin, Request


class RobotsTxtViolationException(Exception):
    pass


class RobotsTxtViolationStrategy(Enum):
    LOG = auto()
    THROW = auto()


class RobotsTxtPluginConfig(BaseModel):
    violation_strategy: RobotsTxtViolationStrategy = RobotsTxtViolationStrategy.LOG


class RobotsTxtPlugin(BeforeRequestPlugin):
    def __init__(self, default_config: RobotsTxtPluginConfig | None = None) -> None:
        self._default_config = default_config or RobotsTxtPluginConfig()
        self._logger = logging.getLogger(__name__)
        self._cache = TTLCache(
            maxsize=sys.maxsize,
            ttl=timedelta(hours=1).total_seconds(),
        )

    @property
    def name(self) -> str:
        return "robots_txt"

    def _extract_host(self, url: str) -> str:
        return urlparse(url).hostname.replace("www.", "")

    async def _get_robots_txt_by_url(self, url: str) -> RobotFileParser | None:
        async with aiohttp.ClientSession() as session:
            response = await session.get(url)
            if response.status != 200:
                return None
            contents = await response.text()
            rfp = RobotFileParser()
            rfp.parse(contents.split("\n"))
            return rfp

    async def _load_robots_txt(self, host: str) -> RobotFileParser | None:
        if cached := self._cache.get(host):
            return cached
        for scheme in ["http", "https"]:
            for host_prefix in ["", "www."]:
                try:
                    robots_txt = await self._get_robots_txt_by_url(
                        f"{scheme}://{host_prefix}{host}/robots.txt"
                    )
                    self._cache[host] = robots_txt
                    if robots_txt:
                        return robots_txt
                except Exception as e:
                    self._logger.error(f"Failed to get robots.txt for {host}: {e}")
                    self._logger.debug(
                        f"Failed to get robots.txt for {host}. Traceback: {format_exc()}"
                    )
        return None

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            RobotsTxtPluginConfig,
            self._default_config,
        )
        host = self._extract_host(request.url)
        robots_txt = await self._load_robots_txt(host)
        if not robots_txt:
            self._logger.debug(
                f"No robots.txt was retrieved for {request.url}. Defaulting to allow"
            )
            return request

        user_agent = (request.headers or {}).get("User-Agent")
        if not user_agent:
            self._logger.debug(
                f"User-Agent is empty while requesting {request.url}. Defaulting to '*'"
            )
            user_agent = "*"

        if not robots_txt.can_fetch(user_agent, request.url):
            error_message = f"robots.txt prohibits requesting {request.url}"
            if config.violation_strategy == RobotsTxtViolationStrategy.THROW:
                raise RobotsTxtViolationException(error_message)
            self._logger.error(
                f"{error_message}. Proceeding because strategy is {config.violation_strategy}"
            )

        return request
