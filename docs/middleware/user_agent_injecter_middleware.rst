#########################
User Agent injector
#########################

This middleware automatically adds ``User-Agent`` header if it's not present. 
It uses `fake-useragent <https://pypi.org/project/fake-useragent/>`_ in order to generate fake real world user agents.

Configuration of the middleware is defined in :py:class:`UserAgentInjecterMiddlewareConfig <sneakpeek.middleware.user_agent_injecter_middleware.UserAgentInjecterMiddlewareConfig>`.

How to configure middleware for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.middleware.user_agent_injecter_middleware import UserAgentInjecterMiddleware, UserAgentInjecterMiddlewareConfig

    server = SneakpeekServer.create(
        ...
        middleware=[
            UserAgentInjecterMiddleware(
                UserAgentInjecterMiddlewareConfig(
                    use_external_data = True,
                    browsers = ["chrome", "firefox"],
                )
            )
        ],
    )


How to override middleware settings for a given scraper:

.. code-block:: python3

    from sneakpeek.middleware.user_agent_injecter_middleware import UserAgentInjecterMiddlewareConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            middleware={
                "user_agent_injecter": UserAgentInjecterMiddlewareConfig(
                    use_external_data = False,
                    browsers = ["chrome", "firefox"],
                )
            }
        ),
    )
