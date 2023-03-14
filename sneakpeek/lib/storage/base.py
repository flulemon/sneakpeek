from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List

from sneakpeek.lib.models import Lease, Scraper, ScraperRun, ScraperRunPriority


class Storage(ABC):
    """Sneakpeeker storage abstract class"""

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
        """Get scraper by ID. Throws :py:class:`ScraperNotFoundError <sneakpeek.lib.errors.ScraperNotFoundError>` if scraper doesn't exist

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

    @abstractmethod
    async def get_scraper_runs(self, scraper_id: int) -> List[ScraperRun]:
        """
        Args:
            scraper_id (int): Scraper ID

        Returns:
            List[ScraperRun]: List of scraper runs
        """
        ...

    @abstractmethod
    async def add_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        """
        Args:
            scraper_run (ScraperRun): Scraper run to add

        Returns:
            ScraperRun: Created scraper run
        """
        ...

    @abstractmethod
    async def update_scraper_run(self, scraper_run: ScraperRun) -> ScraperRun:
        """
        Args:
            scraper_run (ScraperRun): Scraper run to update

        Returns:
            ScraperRun: Updated scraper run
        """
        ...

    @abstractmethod
    async def get_scraper_run(self, scraper_id: int, scraper_run_id: int) -> ScraperRun:
        """Get scraper run by ID.
        Throws :py:class:`ScraperNotFoundError <sneakpeek.lib.errors.ScraperNotFoundError>` if scraper doesn't exist
        Throws :py:class:`ScraperRunNotFoundError <sneakpeek.lib.errors.ScraperRunNotFoundError>` if scraper run doesn't exist

        Args:
            scraper_id (int): Scraper ID
            scraper_run_id (int): Scraper run ID

        Returns:
            ScraperRun: Found scraper run
        """
        ...

    @abstractmethod
    async def dequeue_scraper_run(
        self,
        priority: ScraperRunPriority,
    ) -> ScraperRun | None:
        """Try to dequeue pending scraper run of given priority

        Args:
            priority (ScraperRunPriority): Queue priority

        Returns:
            ScraperRun | None: First pending scraper run or None if the queue is empty
        """
        ...

    @abstractmethod
    async def delete_old_scraper_runs(self, keep_last: int = 50) -> None:
        """Delete old historical scraper runs

        Args:
            keep_last (int, optional): How many historical scraper runs to keep. Defaults to 50.
        """
        ...

    @abstractmethod
    async def get_queue_len(self, priority: ScraperRunPriority) -> int:
        """Get number of pending scraper runs in the queue

        Args:
            priority (ScraperRunPriority): Queue priority

        Returns:
            int: Number of pending scraper runs in the queue
        """
        ...

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

    @abstractmethod
    async def is_read_only(self) -> bool:
        """
        Returns:
            bool: Whether the storage allows modifiying scrapers list and metadata
        """
        ...
