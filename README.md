# Sneakpeek

![CI](https://github.com/flulemon/sneakpeek/actions/workflows/ci.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/sneakpeek-py.svg)](https://badge.fury.io/py/sneakpeek-py)
[![Downloads](https://static.pepy.tech/badge/sneakpeek-py)](https://pepy.tech/project/sneakpeek-py)
[![Documentation Status](https://readthedocs.org/projects/sneakpeek-py/badge/?version=latest)](https://sneakpeek-py.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/flulemon/sneakpeek/branch/main/graph/badge.svg?token=7h45P8qHRG)](https://codecov.io/gh/flulemon/sneakpeek)

**Sneakpeek** - is a framework that helps to quickly and conviniently develop scrapers.
It's the best choice for scrapers that have some specific complex scraping logic that needs
to be run on a constant basis.

## Demo

[Here's a demo project](https://github.com/flulemon/sneakpeek-demo) which uses **Sneakpeek** framework.

You can also run the demo using Docker:

```bash
docker run -it --rm -p 8080:8080 flulemon/sneakpeek-demo
```

Once it has started head over to http://localhost:8080 to play around with it.

## Quick start

So you want to create a new scraper, first you need to make sure you
have installed **Sneakpeek**:

```bash
pip install sneakpeek-py
```

The next step would be implementing scraper logic (or so called scraper
handler):

```python3
# file: demo_scraper.py

import json
import logging

from pydantic import BaseModel

from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler


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
    async def run(self, context: ScraperContext) -> str:
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
```

Now that we have some scraper logic, let\'s make it run periodically. To
do so let\'s configure **SneakpeekServer**:

```python3
# file: main.py

from sneakpeek.models import Scraper, ScraperJobPriority, ScraperSchedule
from sneakpeek.storage.in_memory_storage import (
    InMemoryLeaseStorage,
    InMemoryScraperJobsStorage,
    InMemoryScrapersStorage,
)
from sneakpeek.logging import configure_logging
from sneakpeek.plugins.requests_logging_plugin import RequestsLoggingPlugin
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.server import SneakpeekServer

from demo_scraper import DemoScraper

# For now let's have a static list of scrapers
# but this can as well be a dynamic list which is
# stored in some SQL DB
scrapers = [
    Scraper(
        # Unique ID of the scraper
        id=1,
        # Name of the scraper
        name=f"Demo Scraper",
        # How frequent should scraper be executed
        schedule=ScraperSchedule.EVERY_MINUTE,
        # Our handler name
        handler="demo_scraper",
        # Scraper config, note that params must be successfully
        # deserialized into `DemoScraperParams` class
        config=ScraperConfig(params={"url": url}),
        # Priority of the periodic scraper jobs.
        # Note that manually invoked jobs are always
        # scheduled with `UTMOST` priority
        schedule_priority=ScraperJobPriority.UTMOST,
    )
]

# Define a storage to use to store the list of the scrapers
scrapers_storage = InMemoryScrapersStorage(scrapers)

# Define a jobs storage to use
jobs_storage = InMemoryScraperJobsStorage()

# Define a lease storage for the scheduler to ensure
# that at any point of time there's only 1 active scheduler.
# This eliminates concurrent scrapers execution
lease_storage = InMemoryLeaseStorage()

# Configure server
server = SneakpeekServer.create(
    # List of implemented scraper handlers
    handlers=[DemoScraper()],
    scrapers_storage=scrapers_storage,
    jobs_storage=jobs_storage,
    lease_storage=lease_storage,

    # List of plugins which will be invoked before request
    # is dispatched or after response is received.
    # In the example we use `sneakpeek.plugins.requests_logging_plugin.RequestsLoggingPlugin`
    # which logs all requests and responses being made
    plugins=[RequestsLoggingPlugin()],
)

if __name__ == "__main__":
    configure_logging()
    # Run server (spawns scheduler, API and worker)
    # open http://localhost:8080 and explore UI
    server.serve()
```

Now, the only thing is left is to actually run the server:

```bash
python run main.py
```

That\'s it! Now you can open <http://localhost:8080> and explore the UI
to see how you scraper is being automatically scheduled and executed.

## Local handler testing

You can easily test handler without running full-featured server. Here's how you can do that for the `DemoScraper` that we have developed in the [Quick start](#quick-start).

Add import in the beginning of the file:

```python3
from sneakpeek.runner import LocalRunner
```

And add the following lines to the end of the file:

```python3
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
```

For the argument `LocalRunner.run` takes:

1. An instance of your scraper handler
2. Scraper config
3. **[Optional]** List of plugins that will be used in the handler ([see full list of the plugins here](https://sneakpeek-py.readthedocs.io/en/latest/plugins/index.html))

Now you can run you handler as an ordinary Python script. Given it's in `demo_scraper.py` file you can use:

```bash
python demo_scraper.py
```

## Documentation

For the full documentation please visit [sneakpeek-py.readthedocs.io](https://sneakpeek-py.readthedocs.io/en/latest/)

## Contributing

Please take a look at our [contributing](https://github.com/flulemon/sneakpeek/blob/main/CONTRIBUTING.md) guidelines if you're interested in helping!

## Future plans

- Support for developing and executing scrapers right in the browser
- Plugins for headful and headless browser engines (Selenium and Playwright)
- SQL storage implementation
- Advanced monitoring for the scrapers' health
