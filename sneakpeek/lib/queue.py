import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from sneakpeek.lib.errors import (
    ScraperHasActiveRunError,
    ScraperRunPingFinishedError,
    ScraperRunPingNotStartedError,
)
from sneakpeek.lib.models import (
    UNSET_ID,
    ScraperRun,
    ScraperRunPriority,
    ScraperRunStatus,
)
from sneakpeek.lib.storage.base import Storage
from sneakpeek.metrics import count_invocations, measure_latency

DEFAULT_DEAD_TIMEOUT = timedelta(minutes=5)


class QueueABC(ABC):
    @abstractmethod
    async def enqueue(
        self,
        scraper_id: int,
        priority: ScraperRunPriority,
    ) -> ScraperRun:
        ...

    @abstractmethod
    async def dequeue(self) -> ScraperRun:
        ...

    @abstractmethod
    async def get_queue_len(self, priority: ScraperRunPriority) -> int:
        ...

    @abstractmethod
    async def ping_scraper_run(
        self,
        scraper_id: int,
        scraper_run_id: int,
    ) -> ScraperRun:
        ...

    @abstractmethod
    async def kill_dead_scraper_runs(self, scraper_id: int):
        ...


class Queue:
    def __init__(
        self, storage: Storage, dead_timeout: timedelta = DEFAULT_DEAD_TIMEOUT
    ) -> None:
        self._storage = storage
        self._logger = logging.getLogger(__name__)
        self._dead_timeout = dead_timeout

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def enqueue(
        self,
        scraper_id: int,
        priority: ScraperRunPriority,
    ) -> ScraperRun:
        scraper = await self._storage.get_scraper(scraper_id)
        if await self._has_unfinished_runs(scraper_id):
            raise ScraperHasActiveRunError()
        return await self._storage.add_scraper_run(
            ScraperRun(
                id=UNSET_ID,
                scraper=scraper,
                status=ScraperRunStatus.PENDING,
                priority=priority,
                created_at=datetime.utcnow(),
            )
        )

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def dequeue(self) -> ScraperRun | None:
        for priority in ScraperRunPriority:
            dequeued = await self._storage.dequeue_scraper_run(priority)
            if dequeued:
                dequeued.started_at = datetime.utcnow()
                dequeued.status = ScraperRunStatus.STARTED
                return await self._storage.update_scraper_run(dequeued)
        return None

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def get_queue_len(self, priority: ScraperRunPriority) -> int:
        return await self._storage.get_queue_len(priority)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def ping_scraper_run(
        self,
        scraper_id: int,
        scraper_run_id: int,
    ) -> ScraperRun:
        scraper_run = await self._storage.get_scraper_run(scraper_id, scraper_run_id)
        if scraper_run.status == ScraperRunStatus.PENDING:
            raise ScraperRunPingNotStartedError()
        if scraper_run.status != ScraperRunStatus.STARTED:
            raise ScraperRunPingFinishedError()
        scraper_run.last_active_at = datetime.utcnow()
        return await self._storage.update_scraper_run(scraper_run)

    @count_invocations(subsystem="queue")
    @measure_latency(subsystem="queue")
    async def kill_dead_scraper_runs(self, scraper_id: int) -> List[ScraperRun]:
        runs = await self._storage.get_scraper_runs(scraper_id)
        killed = []
        for run in runs:
            if await self._is_scraper_run_dead(run):
                run.status = ScraperRunStatus.DEAD
                run.finished_at = datetime.utcnow()
                killed.append(await self._storage.update_scraper_run(run))
        return killed

    async def _is_scraper_run_dead(self, scraper_run: ScraperRun) -> bool:
        if scraper_run.status != ScraperRunStatus.STARTED:
            return False
        activity_timestamps = [
            scraper_run.last_active_at,
            scraper_run.started_at,
            scraper_run.created_at,
        ]
        for ts in activity_timestamps:
            if ts and datetime.utcnow() - ts > self._dead_timeout:
                return True
        return False

    async def _has_unfinished_runs(self, scraper_id: int):
        runs = await self._storage.get_scraper_runs(scraper_id)
        return any(
            run
            for run in runs
            if run.status in (ScraperRunStatus.PENDING, ScraperRunStatus.STARTED)
        )
