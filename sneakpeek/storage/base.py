from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List

from sneakpeek.models import Lease, Scraper, ScraperJob, ScraperJobPriority


class ScrapersStorage(ABC):
    """Sneakpeeker storage scraper storage abstract class"""

    @abstractmethod
    async def is_read_only(self) -> bool:
        """
        Returns:
            bool: Whether the storage allows modifiying scrapers list and metadata
        """
        ...

    @abstractmethod
    async def search_scrapers(
        self,
        name_filter: str | None = None,
        max_items: int | None = None,
        offset: int | None = None,
    ) -> List[Scraper]:
        """Search scrapers using given filters

        Args:
            name_filter (str | None, optional): Search scrapers that have given substring in the name. Defaults to None.
            max_items (int | None, optional): Maximum number of items to return. Defaults to None.
            offset (int | None, optional): Offset for search results. Defaults to None.

        Returns:
            List[Scraper]: Found scrapers
        """
        ...

    @abstractmethod
    async def get_scrapers(self) -> List[Scraper]:
        """
        Returns:
            List[Scraper]: List of all available scrapers
        """
        ...

    @abstractmethod
    async def get_scraper(self, id: int) -> Scraper:
        """Get scraper by ID. Throws :py:class:`ScraperNotFoundError <sneakpeek.errors.ScraperNotFoundError>` if scraper doesn't exist

        Args:
            id (int): Scraper ID

        Returns:
            Scraper: Scraper metadata
        """
        ...

    @abstractmethod
    async def maybe_get_scraper(self, id: int) -> Scraper | None:
        """Get scraper by ID. Return None if scraper doesn't exist

        Args:
            id (int): Scraper ID

        Returns:
            Scraper: Scraper metadata
        """
        ...

    @abstractmethod
    async def create_scraper(self, scraper: Scraper) -> Scraper:
        """
        Args:
            scraper (Scraper): Scraper Metadata

        Returns:
            Scraper: Created scraper
        """
        ...

    @abstractmethod
    async def update_scraper(self, scraper: Scraper) -> Scraper:
        """
        Args:
            scraper (Scraper): Scraper Metadata

        Returns:
            Scraper: Updated scraper
        """
        ...

    @abstractmethod
    async def delete_scraper(self, id: int) -> Scraper:
        """
        Args:
            id (int): Scraper ID

        Returns:
            Scraper: Deleted scraper
        """
        ...


class ScraperJobsStorage(ABC):
    """Sneakpeeker storage scraper jobs storage abstract class"""

    @abstractmethod
    async def get_scraper_jobs(self, scraper_id: int) -> List[ScraperJob]:
        """
        Args:
            scraper_id (int): Scraper ID

        Returns:
            List[ScraperJob]: List of scraper jobs
        """
        ...

    @abstractmethod
    async def add_scraper_job(self, scraper_job: ScraperJob) -> ScraperJob:
        """
        Args:
            scraper_job (ScraperJob): scraper job to add

        Returns:
            ScraperJob: Created scraper job
        """
        ...

    @abstractmethod
    async def update_scraper_job(self, scraper_job: ScraperJob) -> ScraperJob:
        """
        Args:
            scraper_job (ScraperJob): scraper job to update

        Returns:
            ScraperJob: Updated scraper job
        """
        ...

    @abstractmethod
    async def get_scraper_job(self, scraper_id: int, scraper_job_id: int) -> ScraperJob:
        """Get scraper job by ID.
        Throws :py:class:`ScraperNotFoundError <sneakpeek.errors.ScraperNotFoundError>` if scraper doesn't exist
        Throws :py:class:`ScraperJobNotFoundError <sneakpeek.errors.ScraperJobNotFoundError>` if scraper job doesn't exist

        Args:
            scraper_id (int): Scraper ID
            scraper_job_id (int): scraper job ID

        Returns:
            ScraperJob: Found scraper job
        """
        ...

    @abstractmethod
    async def dequeue_scraper_job(
        self,
        priority: ScraperJobPriority,
    ) -> ScraperJob | None:
        """Try to dequeue pending scraper job of given priority

        Args:
            priority (ScraperJobPriority): Queue priority

        Returns:
            ScraperJob | None: First pending scraper job or None if the queue is empty
        """
        ...

    @abstractmethod
    async def delete_old_scraper_jobs(self, keep_last: int = 50) -> None:
        """Delete old historical scraper jobs

        Args:
            keep_last (int, optional): How many historical scraper jobs to keep. Defaults to 50.
        """
        ...

    @abstractmethod
    async def get_queue_len(self, priority: ScraperJobPriority) -> int:
        """Get number of pending scraper jobs in the queue

        Args:
            priority (ScraperJobPriority): Queue priority

        Returns:
            int: Number of pending scraper jobs in the queue
        """
        ...


class LeaseStorage(ABC):
    """Sneakpeeker lease storage abstract class"""

    @abstractmethod
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        """Try to acquire lease (global lock).

        Args:
            lease_name (str): Lease name (resource name to be locked)
            owner_id (str): ID of the acquirer (should be the same if you already have the lease and want to prolong it)
            acquire_for (timedelta): For how long lease will be acquired

        Returns:
            Lease | None: Lease metadata if it was acquired, None otherwise
        """
        ...

    @abstractmethod
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        """Release lease (global lock)

        Args:
            lease_name (str): Lease name (resource name to be unlocked)
            owner_id (str): ID of the acquirer
        """
        ...
