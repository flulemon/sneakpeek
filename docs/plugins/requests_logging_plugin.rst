##############################
Requests logging middleware
##############################

Requests logging middleware logs all requests being made and received responses.

Configuration of the plugin is defined in :py:class:`RequestsLoggingPluginConfig <sneakpeek.plugins.requests_logging_plugin.RequestsLoggingPluginConfig>`.

How to configure plugin for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPlugin, RequestsLoggingPluginConfig

    server = SneakpeekServer.create(
        ...
        plugins=[
            RequestsLoggingPlugin(
                RequestsLoggingPluginConfig(
                    log_request=True,
                    log_response=True,
                )
            )
        ],
    )


How to override plugin settings for a given scraper:

.. code-block:: python3

    from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPluginConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            plugins={
                "requests_logging": RequestsLoggingPluginConfig(
                    log_request=True,
                    log_response=False,
                )
            }
        ),
    )
