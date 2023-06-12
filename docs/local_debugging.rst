################################
Local handler debugging
################################

You can easily test handler without running full-featured server. Here's how you can do that for the `DemoScraper` that we have developed in the :doc:`tutorial </quick_start>`.

Add import in the beginning of the file:

.. code-block:: python3

    from sneakpeek.scraper.runner import ScraperRunner


And add the following lines to the end of the file:


.. code-block:: python3


    async def main():
        result = await ScraperRunner.debug_handler(
            DemoScraper(),
            config=ScraperConfig(
                params=DemoScraperParams(
                    start_url="https://www.ycombinator.com/",
                    max_pages=20,
                ).dict(),
            ),
            middlewares=[
                RequestsLoggingMiddleware(),
            ],
        )
        logging.info(f"Finished scraper with result: {result}")

    if __name__ == "__main__":
        asyncio.run(main())


For the argument `ScraperRunner.debug_handler` takes:

1. An instance of your scraper handler
2. Scraper config
3. **[Optional]** Middleware that will be used in the handler (:doc:`see full list of the middleware here </middleware/index>`)

Now you can run you handler as an ordinary Python script. Given it's in `demo_scraper.py` file you can use:

.. code-block:: bash

    python3 demo_scraper.py
