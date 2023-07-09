#########################
Rate limiter
#########################

Rate limiter implements `leaky bucket algorithm <https://en.wikipedia.org/wiki/Leaky_bucket>`_ 
to limit number of requests made to the hosts. If the request is rate limited it can either 
raise an exception or wait until the request won't be limited anymore.

Configuration of the middleware is defined in :py:class:`RateLimiterMiddlewareConfig <sneakpeek.middleware.rate_limiter_middleware.RateLimiterMiddlewareConfig>`.

How to configure middleware for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.middleware.rate_limiter_middleware import RateLimiterMiddleware, RateLimiterMiddlewareConfig

    server = SneakpeekServer.create(
        ...
        middleware=[
            RateLimiterMiddleware(
                RateLimiterMiddlewareConfig(
                    # maximum number of requests in a given time window
                    max_requests = 60,
                    # wait until request won't be rate limited
                    rate_limited_strategy = RateLimitedStrategy.WAIT
                    # only 60 requests per host are allowed within 1 minute
                    time_window = timedelta(minute=1),
                )
            )
        ],
    )


How to override middleware settings for a given scraper:

.. code-block:: python3

    from sneakpeek.middleware.rate_limiter_middleware import RateLimiterMiddlewareConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            middleware={
                "rate_limiter": RateLimiterMiddlewareConfig(
                    # maximum number of requests in a given time window
                    max_requests = 120,
                    # throw RateLimiterException if request is rate limited
                    rate_limited_strategy = RateLimitedStrategy.THROW
                    # only 120 requests per host are allowed within 1 minute
                    time_window = timedelta(minute=1),
                )
            }
        ),
    )
