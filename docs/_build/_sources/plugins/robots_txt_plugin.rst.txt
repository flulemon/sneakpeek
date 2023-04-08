#########################
Robots.txt
#########################

Robots.txt plugin can log and optionally block requests if they are disallowed by website robots.txt. 
If robots.txt is unavailable (e.g. request returns 5xx code) all requests will be allowed.

Configuration of the plugin is defined in :py:class:`RobotsTxtPluginConfig <sneakpeek.plugins.robots_txt_plugin.RobotsTxtPluginConfig>`.

How to configure plugin for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.plugins.robots_txt_plugin import RobotsTxtPlugin, RobotsTxtPluginConfig

    server = SneakpeekServer.create(
        ...
        plugins=[
            ProxyPlugin(
                ProxyPluginConfig(
                    violation_strategy = RobotsTxtViolationStrategy.THROW,
                )
            )
        ],
    )


How to override plugin settings for a given scraper:

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.plugins.robots_txt_plugin import RobotsTxtPluginConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            plugins={
                "robots_txt": ProxyPluginConfig(
                    violation_strategy = RobotsTxtViolationStrategy.LOG,
                )
            }
        ),
    )
