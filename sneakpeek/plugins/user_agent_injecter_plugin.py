from typing import Any

from fake_useragent import UserAgent
from pydantic import BaseModel

from sneakpeek.plugins.utils import parse_config_from_obj
from sneakpeek.scraper_context import BeforeRequestPlugin, Request


class UserAgentInjecterPluginConfig(BaseModel):
    """Plugin configuration"""

    #: Whether to use external data as a fallback
    use_external_data: bool = True

    #: List of browsers which are used to generate user agents
    browsers: list[str] = ["chrome", "edge", "firefox", "safari", "opera"]


class UserAgentInjecterPlugin(BeforeRequestPlugin):
    """
    This plugin automatically adds ``User-Agent`` header if it's not present.
    It uses `fake-useragent <https://pypi.org/project/fake-useragent/>`_ in order to generate fake real world user agents.
    """

    def __init__(
        self, default_config: UserAgentInjecterPluginConfig | None = None
    ) -> None:
        self._default_config = default_config or UserAgentInjecterPluginConfig()
        self._user_agents = UserAgent(
            use_external_data=self._default_config.use_external_data,
            browsers=self._default_config.browsers,
        )

    @property
    def name(self) -> str:
        return "user_agent_injecter"

    async def before_request(
        self,
        request: Request,
        config: Any | None,
    ) -> Request:
        config = parse_config_from_obj(
            config,
            self.name,
            UserAgentInjecterPluginConfig,
            self._default_config,
        )
        if (request.headers or {}).get("User-Agent"):
            return request
        if not request.headers:
            request.headers = {}
        request.headers["User-Agent"] = self._user_agents.random
        return request
