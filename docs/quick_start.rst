#################
Quick start
#################

So you want to create a new scraper, first you need to make sure you have installed **Sneakpeek**:

.. code-block:: bash

    pip install sneakpeek-py

The next step would be implementing scraper logic (or so called scraper handler):

.. code-block:: python3

    # file: demo_scraper.py

    import json
    import logging

    from pydantic import BaseModel

    from sneakpeek.scraper.model import ScraperContextABC, ScraperHandler

    
    # This defines model of handler parameters that are defined 
    # in the scraper config and then passed to the handler
    class DemoScraperParams(BaseModel):
        url: str

    # This is a class which actually implements logic
    # Note that you need to inherit the implementation from 
    # the `sneakpeek.scraper_handler.ScraperHandler`
    class DemoScraper(ScraperHandler):
        # You can have any dependencies you want and pass them
        # in the server configuration
        def __init__(self) -> None:
            self._logger = logging.getLogger(__name__)

        # Each handler must define its name so it later
        # can be referenced in scrapers' configuration
        @property
        def name(self) -> str:
            return "demo_scraper"

        # Some example function that processes the response
        # and extracts valuable information
        async def process_page(self, response: str):
            ...

        # This function is called by the worker to execute the logic
        # The only argument that is passed is `sneakpeek.scraper_context.ScraperContext`
        # It implements basic async HTTP client and also provides parameters
        # that are defined in the scraper config
        async def run(self, context: ScraperContextABC) -> str:
            params = DemoScraperParams.parse_obj(context.params)
            # Perform GET request to the URL defined in the scraper config 
            response = await context.get(params.url)
            response_body = await response.text()

            # Perform some business logic on a response
            result = await self.process_page(response_body)
            
            # Return meaningful job summary - must return a string
            return json.dumps({
                "processed_urls": 1,
                "found_results": len(result),
            })


Now that we have some scraper logic, let's make it run periodically. 
To do so let's configure **SneakpeekServer**:

.. code-block:: python3

    # file: main.py

    import random
    from uuid import uuid4

    from demo.demo_scraper import DemoScraper
    from sneakpeek.logging import configure_logging
    from sneakpeek.middleware.parser import ParserMiddleware
    from sneakpeek.middleware.rate_limiter_middleware import (
        RateLimiterMiddleware,
        RateLimiterMiddlewareConfig,
    )
    from sneakpeek.middleware.requests_logging_middleware import RequestsLoggingMiddleware
    from sneakpeek.middleware.robots_txt_middleware import RobotsTxtMiddleware
    from sneakpeek.middleware.user_agent_injecter_middleware import (
        UserAgentInjecterMiddleware,
        UserAgentInjecterMiddlewareConfig,
    )
    from sneakpeek.queue.in_memory_storage import InMemoryQueueStorage
    from sneakpeek.queue.model import TaskPriority
    from sneakpeek.scheduler.in_memory_lease_storage import InMemoryLeaseStorage
    from sneakpeek.scheduler.model import TaskSchedule
    from sneakpeek.scraper.in_memory_storage import InMemoryScraperStorage
    from sneakpeek.scraper.model import Scraper
    from sneakpeek.server import SneakpeekServer


    def get_server(urls: list[str], is_read_only: bool) -> SneakpeekServer:
        handler = DemoScraper()
        return SneakpeekServer.create(
            handlers=[handler],
            scraper_storage=InMemoryScraperStorage([
                Scraper(
                    id=str(uuid4()),
                    name=f"Demo Scraper",
                    schedule=TaskSchedule.EVERY_MINUTE,
                    handler=handler.name,
                    config=ScraperConfig(params={"start_url": "http://example.com"}),
                    schedule_priority=TaskPriority.NORMAL,
                )
            ]),
            queue_storage=InMemoryQueueStorage(),
            lease_storage=InMemoryLeaseStorage(),
            middlewares=[
                RequestsLoggingMiddleware(),
                RobotsTxtMiddleware(),
                RateLimiterMiddleware(RateLimiterMiddlewareConfig(max_rpm=60)),
                UserAgentInjecterMiddleware(
                    UserAgentInjecterMiddlewareConfig(use_external_data=False)
                ),
                ParserMiddleware(),
            ],
        )


    def main():
        args = parser.parse_args()
        server = get_server(args.urls, args.read_only)
        configure_logging()
        server.serve()


    if __name__ == "__main__":
        main()



Now, the only thing is left is to actually run the server:

.. code-block:: bash

    python3 run main.py

That's it! Now you can open http://localhost:8080 and explore the UI to see
how you scraper is being automatically scheduled and executed.
