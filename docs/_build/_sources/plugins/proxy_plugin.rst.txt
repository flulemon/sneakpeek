#########################
Proxy plugin
#########################

Proxy plugin automatically sets proxy arguments for all HTTP requests.
Configuration of the plugin is defined in :py:class:`ProxyPluginConfig <sneakpeek.plugins.proxy_plugin.ProxyPluginConfig>`.

How to configure plugin for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.plugins.proxy_plugin import ProxyPlugin, ProxyPluginConfig

    server = SneakpeekServer.create(
        ...
        plugins=[
            ProxyPlugin(
                ProxyPluginConfig(
                    proxy = "http://example.proxy.com:3128",
                    proxy_auth = BasicAuth(login="mylogin", password="securepassword"),
                )
            )
        ],
    )


How to override plugin settings for a given scraper:

.. code-block:: python3

    from aiohttp import BasicAuth
    from sneakpeek.plugins.proxy_plugin import ProxyPluginConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            plugins={
                "proxy": ProxyPluginConfig(
                    proxy = "http://example.proxy.com:3128",
                    proxy_auth = BasicAuth(login="mylogin", password="securepassword"),
                )
            }
        ),
    )
