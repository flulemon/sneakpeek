from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from sneakpeek.scraper_config import ScraperConfig

UNSET_ID: int = -1


class ScraperSchedule(str, Enum):
    """
    Scraper schedule options. Note that it's disallowed to have 2 concurrent
    scraper jobs, so if there's an active scraper job new job won't be scheduled
    """

    INACTIVE = "inactive"  #: Scraper won't be automatically scheduled
    EVERY_SECOND = "every_second"  #: Scraper will be scheduled every second
    EVERY_MINUTE = "every_minute"  #: Scraper will be scheduled every minute
    EVERY_HOUR = "every_hour"  #: Scraper will be scheduled every hour
    EVERY_DAY = "every_day"  #: Scraper will be scheduled every day
    EVERY_WEEK = "every_week"  #: Scraper will be scheduled every week
    EVERY_MONTH = "every_month"  #: Scraper will be scheduled every month
    CRONTAB = "crontab"  #: Specify crontab when scraper should be scheduled


class ScraperJobPriority(Enum):
    """Priority of the scraper job"""

    UTMOST = 0  #:
    HIGH = 1  #:
    NORMAL = 2  #:


class ScraperJobStatus(str, Enum):
    """Scraper job status"""

    PENDING = "pending"  #: Scraper job is in the queue
    #: Scraper job was dequeued by the worker and is being processed
    STARTED = "started"
    FAILED = "failed"  #: Scraper job failed
    SUCCEEDED = "succeeded"  #: Scraper job succeeded
    DEAD = "dead"  #: Scraper job was inactive for a while, so scheduler marked it as dead and scheduler can schedule scraper again
    KILLED = "killed"  #: Scraper job was killed by the user


class Scraper(BaseModel):
    """Scraper metadata"""

    id: int  #: Scraper unique identifier
    name: str  #: Scraper name
    schedule: ScraperSchedule  #: Scraper schedule configuration
    schedule_crontab: str | None  #: Must be defined if schedule equals to ``CRONTAB``
    handler: str  #: Name of the scraper handler that implements scraping logic
    config: ScraperConfig  #: Scraper configuration that is passed to the handler
    #: Default priority to enqueue scraper jobs with
    schedule_priority: ScraperJobPriority = ScraperJobPriority.NORMAL
    #: Scraper state (might be useful to optimise scraping, e.g. only process pages that weren't processed in the last jobs)
    state: str | None = None
    #: Timeout for the single scraper job
    timeout_seconds: int | None = None


class ScraperJob(BaseModel):
    """Scraper job metadata"""

    id: int  #: Job unique identifier
    scraper: Scraper  #: Scraper metadata
    status: ScraperJobStatus  #: Scraper job status
    priority: ScraperJobPriority  #: Scraper job priority
    created_at: datetime  #: When the job was created and enqueued
    #: When the job was dequeued and started being processed by the worker
    started_at: datetime | None = None
    last_active_at: datetime | None = None  #: When the job last sent heartbeat
    finished_at: datetime | None = None  #: When the job finished
    result: str | None = None  #: Information with the job result (should be rather small and should summarize the outcome of the scraping)


class Lease(BaseModel):
    """Lease metadata"""

    name: str  #: Lease name (resource name to be locked)
    owner_id: str  #: ID of the acquirer (should be the same if you already have the lease and want to prolong it)
    acquired: datetime  #: Time when the lease was acquired
    acquired_until: datetime  #: Time until the lease is acquired
