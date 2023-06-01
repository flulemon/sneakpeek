################################
Local handler debugging
################################

You can easily test handler without running full-featured server. Here's how you can do that for the `DemoScraper` that we have developed in the :doc:`tutorial </quick_start>`.

Add import in the beginning of the file:

.. code-block:: python3

    from sneakpeek.runner import LocalRunner


And add the following lines to the end of the file:


.. code-block:: python3

    if __name__ == "__main__":
        LocalRunner.run(
            DemoScraper(),
            ScraperConfig(
                params=DemoScraperParams(
                    url="http://google.com",
                ).dict(),
            ),
            plugins=[
                RequestsLoggingPlugin(),
            ],
        )

For the argument `LocalRunner.run` takes:

1. An instance of your scraper handler
2. Scraper config
3. **[Optional]** List of plugins that will be used in the handler (:doc:`see full list of the plugins here </plugins/index>`)

Now you can run you handler as an ordinary Python script. Given it's in `demo_scraper.py` file you can use:

.. code-block:: bash

    python3 demo_scraper.py
