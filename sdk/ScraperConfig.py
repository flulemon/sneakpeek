from dataclasses import dataclass
from typing import Any, Dict, List

from dataclasses_json import dataclass_json


@dataclass
class HttpProxyConfig:
    host: str
    port: int


@dataclass_json
@dataclass
class ScraperConfig:
    proxy: HttpProxyConfig | None
    user_agents: List[str] | None
    use_session: bool = True
    settings: Dict[str, Any] | None = None
