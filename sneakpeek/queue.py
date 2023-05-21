import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from sneakpeek.errors import (
    ScraperHasActiveRunError,
    ScraperJobPingFinishedError,
    ScraperJobPingNotStartedError,
)
from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.models import UNSET_ID, ScraperJob, ScraperJobPriority, ScraperJobStatus
from sneakpeek.storage.base import ScraperJobsStorage, ScrapersStorage

DEFAULT_DEAD_TIMEOUT = timedelta(minutes=5)


class QueueABC(ABC):
    """Sneakpeek scraper job priority queue"""

    @abstractmethod
    async def enqueue(
        self,
        scraper_id: int,
        priority: ScraperJobPriority,
    ) -> ScraperJob:
        """Enqueue scraper job.

        Args:
            scraper_id (int): ID of the scraper to enqueue
            priority (ScraperJobPriority): Priority of the job to enqueue

        Returns:
            ScraperJob: Scraper job metadata

        Raises:
            ScraperNotFoundError: If scraper doesn't exist
            ScraperHasActiveRunError: If there are scraper jobs in ``PENDING`` or ``STARTED`` state
        """
        ...

    @abstractmethod
    async def dequeue(self) -> ScraperJob | None:
        """Try to dequeue a job from the queue.

        Returns:
            ScraperJob: Scraper job metadata if queue wasn't empty or None otherwise
        """
        ...

    @abstractmethod
    async def get_queue_len(self, priority: ScraperJobPriority) -> int:
        """
        Args:
            priority (ScraperJobPriority): Queue priority

        Returns:
            int: Number of pending items in the queue
        """
        ...

    @abstractmethod
    async def ping_scraper_job(
        self,
        scraper_id: int,
        scraper_job_id: int,
    ) -> ScraperJob:
        """Send a heartbeat for the scraper job

        Args:
            scraper_id (int): Scraper ID
            scraper_job_id (int): Scraper job ID

        Returns:
            ScraperJob: Update scraper job metadata

        Raises:
            ScraperNotFoundError: If scraper doesn't exist
            ScraperJobFoundError: If scraper job doesn't exist
            ScraperJobPingNotStartedError: If scraper job is still in the ``PENDING`` state
            ScraperJobPingFinishedError: If scraper job is not in the ``STARTED`` state but it's in finished state (e.g. ``DEAD``)
        """
        ...

    @abstractmethod
    async def kill_dead_scraper_jobs(self, scraper_id: int) -> list[ScraperJob]:
        """Kill dead scraper jobs for the given scraper

        Args:
            scraper_id (int): Scraper ID to kill jobs for

        Returns:
            list[ScraperJob]: List of dead scraper jobs
        """
        ...


class Queue:
    """Default priority queue implementation"""

    def __init__(
        self,
        scrapers_storage: ScrapersStorage,
        scraper_jobs_storage: ScraperJobsStorage,
        dead_timeout: timedelta = DEFAULT_DEAD_TIMEOUT,
    ) -> None:
        """
        Args:
            scrapers_storage (ScrapersStorage): Scrapers storage
            scraper_jobs_storage (ScraperJobsStorage): Scraper jobs storage
            dead_timeout (timedelta, optional): If the scraper job hasn't pinged for the given time period, the job will be marked as dead. Defaults to 5 minute.
        """
        self._scrapers_storage = scrapers_storage
        self._scraper_jobs_storage = scraper_jobs_storage
        self._logger = logging.getLogger(__name__)
        self._dead_timeout = dead_timeout

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def enqueue(
        self,
        scraper_id: int,
        priority: ScraperJobPriority,
    ) -> ScraperJob:
        scraper = await self._scrapers_storage.get_scraper(scraper_id)
        if await self._has_unfinished_runs(scraper_id):
            raise ScraperHasActiveRunError()
        return await self._scraper_jobs_storage.add_scraper_job(
            ScraperJob(
                id=UNSET_ID,
                scraper=scraper,
                status=ScraperJobStatus.PENDING,
                priority=priority,
                created_at=datetime.utcnow(),
            )
        )

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def dequeue(self) -> ScraperJob | None:
        for priority in ScraperJobPriority:
            dequeued = await self._scraper_jobs_storage.dequeue_scraper_job(priority)
            if dequeued:
                dequeued.started_at = datetime.utcnow()
                dequeued.status = ScraperJobStatus.STARTED
                return await self._scraper_jobs_storage.update_scraper_job(dequeued)
        return None

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def get_queue_len(self, priority: ScraperJobPriority) -> int:
        return await self._scraper_jobs_storage.get_queue_len(priority)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def ping_scraper_job(
        self,
        scraper_id: int,
        scraper_job_id: int,
    ) -> ScraperJob:
        scraper_job = await self._scraper_jobs_storage.get_scraper_job(
            scraper_id, scraper_job_id
        )
        if scraper_job.status == ScraperJobStatus.PENDING:
            raise ScraperJobPingNotStartedError()
        if scraper_job.status != ScraperJobStatus.STARTED:
            raise ScraperJobPingFinishedError()
        scraper_job.last_active_at = datetime.utcnow()
        return await self._scraper_jobs_storage.update_scraper_job(scraper_job)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def kill_dead_scraper_jobs(self, scraper_id: int) -> list[ScraperJob]:
        runs = await self._scraper_jobs_storage.get_scraper_jobs(scraper_id)
        killed = []
        for run in runs:
            if await self._is_scraper_job_dead(run):
                run.status = ScraperJobStatus.DEAD
                run.finished_at = datetime.utcnow()
                killed.append(await self._scraper_jobs_storage.update_scraper_job(run))
        return killed

    async def _is_scraper_job_dead(self, scraper_job: ScraperJob) -> bool:
        if scraper_job.status != ScraperJobStatus.STARTED:
            return False
        activity_timestamps = [
            scraper_job.last_active_at,
            scraper_job.started_at,
            scraper_job.created_at,
        ]
        for ts in activity_timestamps:
            if ts and datetime.utcnow() - ts > self._dead_timeout:
                return True
        return False

    async def _has_unfinished_runs(self, scraper_id: int):
        runs = await self._scraper_jobs_storage.get_scraper_jobs(scraper_id)
        return any(
            run
            for run in runs
            if run.status in (ScraperJobStatus.PENDING, ScraperJobStatus.STARTED)
        )
