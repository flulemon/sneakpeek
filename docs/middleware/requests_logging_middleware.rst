##############################
Requests logging middleware
##############################

Requests logging middleware logs all requests being made and received responses.

Configuration of the middleware is defined in :py:class:`RequestsLoggingMiddlewareConfig <sneakpeek.middleware.requests_logging_middleware.RequestsLoggingMiddlewareConfig>`.

How to configure middleware for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.middleware.requests_logging_middleware import RequestsLoggingMiddleware, RequestsLoggingMiddlewareConfig

    server = SneakpeekServer.create(
        ...
        middleware=[
            RequestsLoggingMiddleware(
                RequestsLoggingMiddlewareConfig(
                    log_request=True,
                    log_response=True,
                )
            )
        ],
    )


How to override middleware settings for a given scraper:

.. code-block:: python3

    from sneakpeek.middleware.requests_logging_middleware import RequestsLoggingMiddlewareConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            middleware={
                "requests_logging": RequestsLoggingMiddlewareConfig(
                    log_request=True,
                    log_response=False,
                )
            }
        ),
    )
