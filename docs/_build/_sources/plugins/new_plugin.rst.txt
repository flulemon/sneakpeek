#########################
Adding your own plugin
#########################

It's quite easy to implement your own plugins. Currently only two types of plugins are supported:

* :py:class:`BeforeRequestPlugin <sneakpeek.scraper_context.BeforeRequestPlugin>` - plugin is invoked for each request before it's actually sent to the website
* :py:class:`AfterResponsePlugin <sneakpeek.scraper_context.AfterResponsePlugin>` - plugin is invoked for each received response

=====================================
Before request plugin implementation
=====================================

Each request is wrapped in the :py:class:`Request <sneakpeek.scraper_context.Request>` class 
and you can modify its parameters before it's dispatched, here's the schema:

.. code-block:: python3

  @dataclass
  class Request:
      method: HttpMethod
      url: str
      headers: HttpHeaders | None = None
      kwargs: dict[str, Any] | None = None

Here's the example of the plugin which logs each request URL:

.. code-block:: python3

  import logging
  from typing import Any

  import aiohttp
  from pydantic import BaseModel

  from sneakpeek.plugins.utils import parse_config_from_obj
  from sneakpeek.scraper_context import BeforeRequestPlugin, Request


  # Each plugin can be configured, its configuration can be
  # set globally for all requests or it can be overriden for
  # specific scrapers
  class MyLoggingPluginConfig(BaseModel):
      some_param: str = "defaul value"

  class MyPlugin(BeforeRequestPlugin):
    """Plugin description"""

    def __init__(self, default_config: MyLoggingPluginConfig | None = None) -> None:
        self._default_config = default_config or MyLoggingPluginConfig()
        self._logger = logging.getLogger(__name__)

    # The name property is mandatory, it's used in scraper config to override 
    # plugin configuration for the given scraper
    @property
    def name(self) -> str:
        return "my_plugin"

    async def before_request(self, request: Request, config: Any | None) -> Request:
        # This converts freeform dictionary into a typed config (it's optional)
        config = parse_config_from_obj(
            config,
            self.name,
            MyLoggingPluginConfig,
            self._default_config,
        )
        self._logger.info(f"Making {request.method.upper()} to {request.url}. {config.some_param}")
        return request


=====================================
After response plugin implementation
=====================================

After response plugins recieve both request and response objects. Response is `aiohttp.ClientResponse <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse>`_ object.


Here's the example of the plugin which logs each response body:

.. code-block:: python3

  import logging
  from typing import Any

  import aiohttp
  from pydantic import BaseModel

  from sneakpeek.plugins.utils import parse_config_from_obj
  from sneakpeek.scraper_context import AfterResponsePlugin, Request


  # Each plugin can be configured, its configuration can be
  # set globally for all requests or it can be overriden for
  # specific scrapers
  class MyLoggingPluginConfig(BaseModel):
      some_param: str = "defaul value"

  class MyPlugin(AfterResponsePlugin):
    """Plugin description"""

    def __init__(self, default_config: MyLoggingPluginConfig | None = None) -> None:
        self._default_config = default_config or MyLoggingPluginConfig()
        self._logger = logging.getLogger(__name__)

    # The name property is mandatory, it's used in scraper config to override 
    # plugin configuration for the given scraper
    @property
    def name(self) -> str:
        return "my_plugin"

    async def after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None,
    ) -> aiohttp.ClientResponse:
        config = parse_config_from_obj(
            config,
            self.name,
            MyLoggingPluginConfig,
            self._default_config,
        )
        response_body = await response.text()
        self._logger.info(f"Made {request.method.upper()} request to {request.url} - received: status={response.status} body={response_body}")
        return response
