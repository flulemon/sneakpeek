################################
Implementing your own middleware
################################

The interface for middleware is defined in :py:class:`Middleware <sneakpeek.scraper.model.Middleware>`. 
There are 3 ways how middleware can be used:
1. Perform custom logic before request is processed (implement `on_request` method)
2. Perform custom logic before response is returned to the scraper logic (implement `on_response` method)
3. Provide some additional functionality a for the scraper implementation - scraper can call any middleware method using :py:class:`ScraperContext <sneakpeek.scraper.model.ScraperContextABC>`. Each middleware is added as an attribute to the passed context, so you can call it like :code:`context.<middleware_name>.<middleware_method>(...)`


=====================================
Middleware implementation example
=====================================

-----------------------
On request middleware
-----------------------
Each request is wrapped in the :py:class:`Request <sneakpeek.scraper.model.Request>` class 
and you can modify its parameters before it's dispatched, here's the schema:

.. code-block:: python3

  @dataclass
  class Request:
      method: HttpMethod
      url: str
      headers: HttpHeaders | None = None
      kwargs: dict[str, Any] | None = None

Here's the example of the middleware which logs each request URL:

.. code-block:: python3

  import logging
  from typing import Any

  import aiohttp
  from pydantic import BaseModel

  from sneakpeek.middlewares.utils import parse_config_from_obj
  from sneakpeek.scraper.model import Middleware, Request


  # Each middleware can be configured, its configuration can be
  # set globally for all requests or it can be overriden for
  # specific scrapers
  class MyLoggingMiddlewareConfig(BaseModel):
      some_param: str = "defaul value"

  class MyMiddleware(BeforeRequestMiddleware):
    """Middleware description"""

    def __init__(self, default_config: MyLoggingMiddlewareConfig | None = None) -> None:
        self._default_config = default_config or MyLoggingMiddlewareConfig()
        self._logger = logging.getLogger(__name__)

    # The name property is mandatory, it's used in scraper config to override 
    # middleware configuration for the given scraper
    @property
    def name(self) -> str:
        return "my_middleware"

    async def on_request(self, request: Request, config: Any | None) -> Request:
        # This converts freeform dictionary into a typed config (it's optional)
        config = parse_config_from_obj(
            config,
            self.name,
            MyLoggingMiddlewareConfig,
            self._default_config,
        )
        self._logger.info(f"Making {request.method.upper()} to {request.url}. {config.some_param}")
        return request



-----------------------
On response middleware
-----------------------

On response method recieves both request and response objects. Response is `aiohttp.ClientResponse <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse>`_ object.


Here's the example of the middleware which logs each response body:

.. code-block:: python3

  import logging
  from typing import Any

  import aiohttp
  from pydantic import BaseModel

  from sneakpeek.middleware.base import parse_config_from_obj
  from sneakpeek.scraper.model import Middleware, Request


  # Each middleware can be configured, its configuration can be
  # set globally for all requests or it can be overriden for
  # specific scrapers
  class MyLoggingMiddlewareConfig(BaseModel):
      some_param: str = "defaul value"


  class MyOnResponseMiddleware(Middleware):
    """Middleware description"""

    def __init__(self, default_config: MyLoggingMiddlewareConfig | None = None) -> None:
        self._default_config = default_config or MyLoggingMiddlewareConfig()
        self._logger = logging.getLogger(__name__)

    # The name property is mandatory, it's used in scraper config to override 
    # middleware configuration for the given scraper
    @property
    def name(self) -> str:
        return "my_middleware"

    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None,
    ) -> aiohttp.ClientResponse:
        config = parse_config_from_obj(
            config,
            self.name,
            MyLoggingMiddlewareConfig,
            self._default_config,
        )
        response_body = await response.text()
        self._logger.info(f"Made {request.method.upper()} request to {request.url} - received: status={response.status} body={response_body}")
        return response

------------------------
Functional middleware
------------------------

If the middleware doesn't need to interact with the request or response you can derive it 
from :py:class:`BaseMiddleware <sneakpeek.middleware.base.BaseMiddleware>`, so that both
`on_request` and `on_response` method are implemented as pass-through.

Here's an example of such implementation

.. code-block:: python3

  import logging
  from typing import Any

  from sneakpeek.middleware.base import parse_config_from_obj, BaseMiddleware


  class MyFunctionalMiddleware(BaseMiddleware):
    """Middleware description"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    # The name property is mandatory, it's used in scraper config to override 
    # middleware configuration for the given scraper
    @property
    def name(self) -> str:
        return "my_middleware"

    # This function will be available for scrapers by using
    # `context.my_middleware.custom_funct(some_arg)`
    def custom_func(self, arg1: Any) -> Any:
        return do_something(arg1)

        