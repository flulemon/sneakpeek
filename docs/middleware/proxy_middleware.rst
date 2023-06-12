#########################
Proxy middleware
#########################

Proxy middleware automatically sets proxy arguments for all HTTP requests.
Configuration of the middleware is defined in :py:class:`ProxyMiddlewareConfig <sneakpeek.middleware.proxy_middleware.ProxyMiddlewareConfig>`.

How to configure middleware for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.middleware.proxy_middleware import ProxyMiddleware, ProxyMiddlewareConfig

    server = SneakpeekServer.create(
        ...
        middleware=[
            ProxyMiddleware(
                ProxyMiddlewareConfig(
                    proxy = "http://example.proxy.com:3128",
                    proxy_auth = BasicAuth(login="mylogin", password="securepassword"),
                )
            )
        ],
    )


How to override middleware settings for a given scraper:

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.middleware.proxy_middleware import ProxyMiddlewareConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            middleware={
                "proxy": ProxyMiddlewareConfig(
                    proxy = "http://example.proxy.com:3128",
                    proxy_auth = BasicAuth(login="mylogin", password="securepassword"),
                )
            }
        ),
    )
