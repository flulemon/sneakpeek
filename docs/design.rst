#################
Design
#################

.. contents:: Table of contents

**Sneakpeek** has 6 core components:

* Scrapers storage - stores list of scrapers and its metadata.
* Jobs queue - populated by the scheduler or user and is consumed by the workers
* Lease storage - stores lease (global lock) for scheduler, to make sure there's only 1 active scheduler at all times.
* Scheduler - schedules scrapers defined in the scrapers storage
* Worker - consumes jobs queue and executes scrapers logic
* API - provides JsonRPC API for interacting with the system

All of the components are run by the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>`.

================
Scrapers Storage
================

Storage must implement this abstract class :py:class:`sneakpeek.storage.base.ScrapersStorage`.
Following methods are mandatory to implement:

* :py:meth:`get_scrapers <sneakpeek.storage.base.ScrapersStorage.get_scrapers>` - get list of all scrapers
* :py:meth:`get_scraper <sneakpeek.storage.base.ScrapersStorage.get_scraper>` - get scraper by ID
* :py:meth:`is_read_only <sneakpeek.storage.base.ScrapersStorage.is_read_only>` - whether the storage allows modifications of the scrapers list and its metadata

Following methods are optional to implement:

* :py:meth:`create_scraper <sneakpeek.storage.base.ScrapersStorage.create_scraper>` - create a new scraper
* :py:meth:`delete_scraper <sneakpeek.storage.base.ScrapersStorage.delete_scraper>` - delete scraper by ID
* :py:meth:`update_scraper <sneakpeek.storage.base.ScrapersStorage.update_scraper>` - update existing scraper
* :py:meth:`maybe_get_scraper <sneakpeek.storage.base.ScrapersStorage.maybe_get_scraper>` - get scraper by ID if it exists
* :py:meth:`search_scrapers <sneakpeek.storage.base.ScrapersStorage.search_scrapers>` - search scrapers using given filters

Currently there 2 storage implementations:

* :py:class:`InMemoryScrapersStorage <sneakpeek.storage.in_memory_storage.InMemoryScrapersStorage>` - in-memory storage. Should either be used in **development** environment or if the list of scrapers is static and wouldn't be changed.
* :py:class:`RedisScrapersStorage <sneakpeek.storage.in_memory_storage.RedisScrapersStorage>` - redis storage.

================
Jobs queue
================

Jobs queue must implement this abstract class :py:class:`sneakpeek.storage.base.ScraperJobsStorage`.
Following methods must be implemented:

* :py:meth:`get_scraper_jobs <sneakpeek.storage.base.ScraperJobsStorage.get_scraper_jobs>` - get scraper jobs by scraper ID
* :py:meth:`add_scraper_job <sneakpeek.storage.base.ScraperJobsStorage.add_scraper_job>` - add new scraper job
* :py:meth:`update_scraper_job <sneakpeek.storage.base.ScraperJobsStorage.update_scraper_job>` - update existing scraper job
* :py:meth:`get_scraper_job <sneakpeek.storage.base.ScraperJobsStorage.get_scraper_job>` - get existing scraper job by scraper ID and scraper job ID
* :py:meth:`dequeue_scraper_job <sneakpeek.storage.base.ScraperJobsStorage.dequeue_scraper_job>` - dequeue scraper job from queue with given priority
* :py:meth:`delete_old_scraper_jobs <sneakpeek.storage.base.ScraperJobsStorage.delete_old_scraper_jobs>` - delete old historical scraper jobs
* :py:meth:`get_queue_len <sneakpeek.storage.base.ScraperJobsStorage.get_queue_len>` - get number of pending scraper jobs in the queue with given priority

Currently there 2 storage implementations:

* :py:class:`InMemoryScraperJobsStorage <sneakpeek.storage.in_memory_storage.InMemoryScraperJobsStorage>` - in-memory storage. Should only be used in **development** environment.
* :py:class:`RedisScraperJobsStorage <sneakpeek.storage.in_memory_storage.RedisScraperJobsStorage>` - redis storage.

================
Lease storage
================

Lease storage is used by scheduler to ensure that at any point of time there's no more 
than 1 active scheduler instance which can enqueue scraper jobs. This disallows concurrent
execution of the scraper.

Lease storage must implement this abstract class :py:class:`sneakpeek.storage.base.LeaseStorage`.
Following methods must be implemented:

* :py:meth:`maybe_acquire_lease <sneakpeek.storage.base.LeaseStorage.maybe_acquire_lease>` - try to acquire lease (or global lock)
* :py:meth:`release_lease <sneakpeek.storage.base.LeaseStorage.release_lease>` - release acquired lease

Currently there 2 storage implementations:

* :py:class:`InMemoryLeaseStorage <sneakpeek.storage.in_memory_storage.InMemoryLeaseStorage>` - in-memory storage. Should only be used in **development** environment.
* :py:class:`RedisLeaseStorage <sneakpeek.storage.in_memory_storage.RedisLeaseStorage>` - redis storage.

================
Scheduler
================

Scheduler is responsible for:

* scheduling scrapers based on their configuration. 
* finding scraper jobs that haven't sent a heartbeat for a while and mark them as dead
* cleaning up jobs queue from old historical scraper jobs
* exporting metrics on number of pending jobs in the queue

As for now there's only one implementation :py:class:`Scheduler <sneakpeek.scheduler.Scheduler>` 
that uses `APScheduler <https://apscheduler.readthedocs.io/en/3.x/>`_.

================
Worker
================

Worker constantly tries to dequeue a job and executes dequeued jobs.
As for now there's only one implementation :py:class:`Worker <sneakpeek.worker.Worker>`.


================
API
================

Sneakpeek implements:

* JsonRPC to programmatically interact with the system, it exposes following methods (available at ``/api/v1/jsonrpc``):
  * CRUD methods to add, modify and delete scrapers
  * Get list of scraper's jobs
  * Enqueue scraper jobs
* UI that allows you to interact with the system
* Swagger documentation (available at ``/api``)
* Copy of this documentation (available at ``/docs``)
