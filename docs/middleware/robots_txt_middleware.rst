#########################
Robots.txt
#########################

Robots.txt middleware can log and optionally block requests if they are disallowed by website robots.txt. 
If robots.txt is unavailable (e.g. request returns 5xx code) all requests will be allowed.

Configuration of the middleware is defined in :py:class:`RobotsTxtMiddlewareConfig <sneakpeek.middleware.robots_txt_middleware.RobotsTxtMiddlewareConfig>`.

How to configure middleware for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.middleware.robots_txt_middleware import RobotsTxtMiddleware, RobotsTxtMiddlewareConfig

    server = SneakpeekServer.create(
        ...
        middleware=[
            ProxyMiddleware(
                ProxyMiddlewareConfig(
                    violation_strategy = RobotsTxtViolationStrategy.THROW,
                )
            )
        ],
    )


How to override middleware settings for a given scraper:

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.middleware.robots_txt_middleware import RobotsTxtMiddlewareConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            middleware={
                "robots_txt": ProxyMiddlewareConfig(
                    violation_strategy = RobotsTxtViolationStrategy.LOG,
                )
            }
        ),
    )
