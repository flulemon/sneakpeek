from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from sneakpeek.scraper_config import ScraperConfig

UNSET_ID: int = -1


class ScraperSchedule(str, Enum):
    INACTIVE = "inactive"
    EVERY_SECOND = "every_second"
    EVERY_MINUTE = "every_minute"
    EVERY_HOUR = "every_hour"
    EVERY_DAY = "every_day"
    EVERY_WEEK = "every_week"
    EVERY_MONTH = "every_month"
    CRONTAB = "crontab"


class ScraperRunPriority(Enum):
    UTMOST = 0
    HIGH = 1
    NORMAL = 2


class ScraperRunStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    DEAD = "dead"
    KILLED = "killed"


class Scraper(BaseModel):
    id: int
    name: str
    schedule: ScraperSchedule
    schedule_crontab: str | None
    handler: str
    config: ScraperConfig
    schedule_priority: ScraperRunPriority = ScraperRunPriority.NORMAL


class ScraperRun(BaseModel):
    id: int
    scraper: Scraper
    status: ScraperRunStatus
    priority: ScraperRunPriority
    created_at: datetime
    started_at: datetime | None = None
    last_active_at: datetime | None = None
    finished_at: datetime | None = None
    result: str | None = None


class Lease(BaseModel):
    name: str
    owner_id: str
    acquired: datetime
    acquired_until: datetime
