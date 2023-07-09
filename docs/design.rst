#################
Design
#################

.. contents:: Table of contents

**Sneakpeek** has 6 core components:

* Scrapers storage - stores list of scrapers and its metadata.
* Tasks queue - populated by the scheduler or user and is consumed by the queue consumers
* Lease storage - stores lease (global lock) for scheduler, to make sure there's only 1 active scheduler at all times.
* Scheduler - schedules periodic tasks using scrapers in the storage
* Consumer - consumes tasks queue and executes tasks logic (e.g. scraper logic)
* API - provides JsonRPC API for interacting with the system

All of the components are run by the :py:class:`SneakpeekServer <sneakpeek.server.SneakpeekServer>`.

================
Scrapers Storage
================

Scraper storage interface is defined in :py:class:`sneakpeek.scraper.model.ScraperStorageABC`.

* :py:class:`InMemoryScraperStorage <sneakpeek.scraper.in_memory_storage.InMemoryScraperStorage>` - in-memory storage. Should either be used in **development** environment or if the list of scrapers is static and wouldn't be changed.
* :py:class:`RedisScraperStorage <sneakpeek.storage.redis_storage.RedisScraperStorage>` - redis storage.

================
Tasks queue
================

Tasks queue consists of three components:
* :py:class:`Storage <sneakpeek.queue.model.QueueStorageABC>` - tasks storage
* :py:class:`Storage <sneakpeek.queue.model.QueueABC>` - queue implementation
* :py:class:`Storage <sneakpeek.queue.model.Consumer>` - queue consumer implementation

Currently there 2 storage implementations:

* :py:class:`InMemoryQueueStorage <sneakpeek.queue.in_memory_storage.InMemoryQueueStorage>` - in-memory storage. Should only be used in **development** environment.
* :py:class:`RedisQueueStorage <sneakpeek.queue.redis_storage.RedisQueueStorage>` - redis storage.

================
Lease storage
================

Lease storage is used by scheduler to ensure that at any point of time there's no more 
than 1 active scheduler instance which can enqueue scraper jobs. This disallows concurrent
execution of the scraper.

Lease storage interface is defined in :py:class:`LeaseStorageABC <sneakpeek.scheduler.model.LeaseStorageABC>`.

Currently there 2 storage implementations:

* :py:class:`InMemoryLeaseStorage <sneakpeek.scheduler.in_memory_lease_storage.InMemoryLeaseStorage>` - in-memory storage. Should only be used in **development** environment.
* :py:class:`RedisLeaseStorage <sneakpeek.scheduler.redis_lease_storage.RedisLeaseStorage>` - redis storage.

================
Scheduler
================

:py:class:`Scheduler <sneakpeek.scheduler.model.SchedulerABC>` is responsible for:

* scheduling scrapers based on their configuration. 
* finding scraper jobs that haven't sent a heartbeat for a while and mark them as dead
* cleaning up jobs queue from old historical scraper jobs
* exporting metrics on number of pending jobs in the queue

As for now there's only one implementation :py:class:`Scheduler <sneakpeek.scheduler.scheduler.Scheduler>` 
that uses `APScheduler <https://apscheduler.readthedocs.io/en/3.x/>`_.

================
Queue consumer
================

Consumer constantly tries to dequeue a job and executes dequeued jobs.
As for now there's only one implementation :py:class:`Worker <sneakpeek.queue.consumer.Consumer>`.


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
