#################
Overview
#################

**Sneakpeek** - is a platform to author, schedule and monitor scrapers in an easy, fast and extensible way.
It's the best choice for scrapers that have some specific complex scraping logic that needs
to be run on a constant basis.

Key features
############

- Horizontally scalable
- Robust scraper scheduler and priority task queue
- Multiple storage implementations to persist scrapers' configs, tasks, logs, etc.
- JSON RPC API to manage the platform programmatically
- Useful UI to manage all of your scrapers
- Scraper IDE to enable you developing scrapers right in your browser
- Easily extendable via middleware

Demo
####

[Here's a demo project](https://github.com/flulemon/sneakpeek-demo) which uses **Sneakpeek** framework.

You can also run the demo using Docker:

.. code-block:: bash

   docker run -it --rm -p 8080:8080 flulemon/sneakpeek-demo


Once it has started head over to http://localhost:8080 to play around with it.

Table of contents
==================

.. toctree::
   :maxdepth: 2

   self
   quick_start
   local_debugging
   design
   deployment
   middleware/index
   api

Indices
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`