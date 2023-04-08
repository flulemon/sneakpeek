#########################
User Agent injector
#########################

This plugin automatically adds ``User-Agent`` header if it's not present. 
It uses `fake-useragent <https://pypi.org/project/fake-useragent/>`_ in order to generate fake real world user agents.

Configuration of the plugin is defined in :py:class:`UserAgentInjecterPluginConfig <sneakpeek.plugins.user_agent_injecter_plugin.UserAgentInjecterPluginConfig>`.

How to configure plugin for the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>` (will be used globally for all requests):

.. code-block:: python3

    from sneakpeek.plugins.user_agent_injecter_plugin import UserAgentInjecterPlugin, UserAgentInjecterPluginConfig

    server = SneakpeekServer.create(
        ...
        plugins=[
            UserAgentInjecterPlugin(
                UserAgentInjecterPluginConfig(
                    use_external_data = True,
                    browsers = ["chrome", "firefox"],
                )
            )
        ],
    )


How to override plugin settings for a given scraper:

.. code-block:: python3

    from sneakpeek.plugins.user_agent_injecter_plugin import UserAgentInjecterPluginConfig

    scraper = Scraper(
        ...
        config=ScraperConfig(
            ...
            plugins={
                "user_agent_injecter": UserAgentInjecterPluginConfig(
                    use_external_data = False,
                    browsers = ["chrome", "firefox"],
                )
            }
        ),
    )
