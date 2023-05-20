from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from sneakpeek.lib.errors import ScraperJobPingFinishedError
from sneakpeek.lib.models import (
    Scraper,
    ScraperJob,
    ScraperJobPriority,
    ScraperJobStatus,
    ScraperSchedule,
)
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import ScraperJobsStorage
from sneakpeek.runner import LocalRunner, Runner, RunnerABC
from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import ScraperContext
from sneakpeek.scraper_handler import ScraperHandler

FAILURE_TEXT = "failure"
RESULT = "result"

EXISTING_SCRAPER_HANDLER = "ExistingScraperHandler"
NON_EXISTING_SCRAPER_HANDLER = "NonExistingScraperHandler"


class TestScraper(ScraperHandler):
    def __init__(self, succees_func, failure_func) -> None:
        self.success_func = succees_func
        self.failure_func = failure_func

    @property
    def name(self) -> str:
        return EXISTING_SCRAPER_HANDLER

    async def run(self, context: ScraperContext) -> str:
        await context.update_scraper_state("some state")
        await context.ping_session()
        if context.params["fail"]:
            return await self.failure_func()
        return await self.success_func()


@pytest.fixture
def scraper_handler_succeeding_impl():
    yield AsyncMock(return_value=RESULT)


@pytest.fixture
def scraper_handler_failing_impl():
    yield AsyncMock(side_effect=Exception(FAILURE_TEXT))


@pytest.fixture
def scraper_handler(
    scraper_handler_succeeding_impl,
    scraper_handler_failing_impl,
) -> ScraperHandler:
    yield TestScraper(scraper_handler_succeeding_impl, scraper_handler_failing_impl)


@pytest.fixture
def queue():
    yield AsyncMock()


@pytest.fixture
def storage():
    yield AsyncMock()


@pytest.fixture
def runner(
    scraper_handler: ScraperHandler, queue: QueueABC, storage: ScraperJobsStorage
) -> RunnerABC:
    yield Runner(
        handlers=[scraper_handler],
        queue=queue,
        storage=storage,
    )


@pytest.fixture
def local_runner() -> LocalRunner:
    yield LocalRunner()


def get_scraper_job(
    *,
    fail: bool,
    existing: bool,
    status: ScraperJobStatus = ScraperJobStatus.STARTED,
) -> ScraperJob:
    return ScraperJob(
        id=100,
        scraper=Scraper(
            id=1,
            name="test_scraper",
            schedule=ScraperSchedule.INACTIVE,
            handler=(
                EXISTING_SCRAPER_HANDLER if existing else NON_EXISTING_SCRAPER_HANDLER
            ),
            config=ScraperConfig(params={"fail": fail}),
        ),
        status=status,
        priority=ScraperJobPriority.NORMAL,
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_runner_run_job_success(
    scraper_handler_succeeding_impl: AsyncMock,
    scraper_handler_failing_impl: AsyncMock,
    runner: RunnerABC,
    queue: QueueABC,
    storage: ScraperJobsStorage,
) -> None:
    job = get_scraper_job(fail=False, existing=True)
    await runner.run(job)
    scraper_handler_succeeding_impl.assert_awaited_once()
    scraper_handler_failing_impl.assert_not_awaited()
    queue.ping_scraper_job.assert_awaited()
    assert job.status == ScraperJobStatus.SUCCEEDED
    assert job.result == RESULT
    storage.update_scraper_job.assert_awaited_once_with(job)


@pytest.mark.asyncio
async def test_runner_run_job_failure(
    scraper_handler_succeeding_impl: AsyncMock,
    scraper_handler_failing_impl: AsyncMock,
    runner: RunnerABC,
    queue: QueueABC,
    storage: ScraperJobsStorage,
) -> None:
    job = get_scraper_job(fail=True, existing=True)
    await runner.run(job)
    scraper_handler_succeeding_impl.assert_not_awaited()
    scraper_handler_failing_impl.assert_awaited_once()
    queue.ping_scraper_job.assert_awaited()
    assert job.status == ScraperJobStatus.FAILED
    assert job.result == FAILURE_TEXT
    storage.update_scraper_job.assert_awaited_once_with(job)


@pytest.mark.asyncio
async def test_runner_run_job_non_existent(
    runner: RunnerABC,
    queue: QueueABC,
    storage: ScraperJobsStorage,
) -> None:
    job = get_scraper_job(fail=False, existing=False)
    await runner.run(job)
    queue.ping_scraper_job.assert_awaited()
    assert job.status == ScraperJobStatus.FAILED
    assert "NonExistingScraperHandler" in job.result
    storage.update_scraper_job.assert_awaited_once_with(job)


@pytest.mark.asyncio
async def test_runner_ping_killed(
    runner: RunnerABC,
    queue: QueueABC,
    storage: ScraperJobsStorage,
) -> None:
    job = get_scraper_job(fail=False, existing=False, status=ScraperJobStatus.KILLED)
    queue.ping_scraper_job.side_effect = ScraperJobPingFinishedError()
    await runner.run(job)
    queue.ping_scraper_job.assert_awaited()
    # job status is not overriden
    assert job.status == ScraperJobStatus.KILLED
    storage.update_scraper_job.assert_awaited_once_with(job)


def test_local_runner_job_succeeds(
    scraper_handler_succeeding_impl: AsyncMock,
    scraper_handler_failing_impl: AsyncMock,
    scraper_handler: ScraperHandler,
    local_runner: LocalRunner,
):
    config = ScraperConfig(params={"fail": False})
    local_runner.run(scraper_handler, config)
    scraper_handler_succeeding_impl.assert_awaited_once()
    scraper_handler_failing_impl.assert_not_awaited()


def test_local_runner_job_fails(
    scraper_handler_succeeding_impl: AsyncMock,
    scraper_handler_failing_impl: AsyncMock,
    scraper_handler: ScraperHandler,
    local_runner: LocalRunner,
):
    config = ScraperConfig(params={"fail": True})
    local_runner.run(scraper_handler, config)
    scraper_handler_succeeding_impl.assert_not_awaited()
    scraper_handler_failing_impl.assert_awaited_once()
