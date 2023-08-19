# Sneakpeek

![CI](https://github.com/flulemon/sneakpeek/actions/workflows/ci.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/sneakpeek-py.svg)](https://badge.fury.io/py/sneakpeek-py)
[![Downloads](https://static.pepy.tech/badge/sneakpeek-py)](https://pepy.tech/project/sneakpeek-py)
[![Documentation Status](https://readthedocs.org/projects/sneakpeek-py/badge/?version=latest)](https://sneakpeek-py.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/flulemon/sneakpeek/branch/main/graph/badge.svg?token=7h45P8qHRG)](https://codecov.io/gh/flulemon/sneakpeek)

**Sneakpeek** - is a platform to author, schedule and monitor scrapers in an easy, fast and extensible way.
It's the best choice for scrapers that have some specific complex scraping logic that needs
to be run on a constant basis.

## Key features

- Horizontally scalable
- Robust scraper scheduler and priority task queue
- Multiple storage implementations to persist scrapers' configs, tasks, logs, etc.
- JSON RPC API to manage the platform programmatically
- Useful UI to manage all of your scrapers
- Scraper IDE to enable you developing scrapers right in your browser
- Easily extendable via middleware

## Demo

[Here's a demo project](https://github.com/flulemon/sneakpeek-demo) which uses **Sneakpeek** framework.

You can also run the demo using Docker:

```bash
docker run -it --rm -p 8080:8080 flulemon/sneakpeek-demo
```

Once it has started head over to http://localhost:8080 to play around with it.

## Documentation

For the full documentation please visit [sneakpeek-py.readthedocs.io](https://sneakpeek-py.readthedocs.io/en/latest/)

## Contributing

Please take a look at our [contributing](https://github.com/flulemon/sneakpeek/blob/main/CONTRIBUTING.md) guidelines if you're interested in helping!

## Future plans

- Headful and headless browser engines middleware (Selenium and Playwright)
- SQL and AmazonDB storage implementation
- Advanced monitoring for the scrapers' health
