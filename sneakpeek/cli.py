import argparse
import asyncio
import logging

import uvicorn

from sneakpeek.api import create_api
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage.in_memory_storage import InMemoryStorage
from sneakpeek.runner import Runner
from sneakpeek.scheduler import Scheduler
from sneakpeek.worker import Worker

parser = argparse.ArgumentParser(
    description="sneakpeek - a toolbox for creating scrapers"
)

parser.add_argument(
    "--api", action=argparse.BooleanOptionalAction, help="Run sneakpeek API server"
)
parser.add_argument(
    "--scheduler",
    action=argparse.BooleanOptionalAction,
    help="Run sneakpeek scheduler (schedules scraper jobs)",
)
parser.add_argument(
    "--worker",
    action=argparse.BooleanOptionalAction,
    help="Run sneakpeek worker (executes scrapers)",
)

parser.add_argument("--api-port", default=8080, help="sneakpeek API server port")
parser.add_argument(
    "--worker-concurrency",
    default=50,
    help="Maximum number of concurrently executed scrapers",
)

parser.add_argument(
    "--storage",
    default="in-memory",
    choices=["in-memory"],
    help="sneakpeek storage to use",
)

args = parser.parse_args()


async def main(args):
    storage = InMemoryStorage()
    queue = Queue(storage)
    loop = asyncio.get_running_loop()
    if args.scheduler:
        scheduler = Scheduler(storage, queue)
        loop.create_task(scheduler.start())
    if args.worker:
        runner = Runner(queue, storage)
        worker = Worker(runner, queue, max_concurrency=args.worker_concurrency)
        loop.create_task(worker.start())
    if args.api:
        config = uvicorn.Config(create_api(storage, queue), port=args.api_port)
        server = uvicorn.Server(config)
        loop.create_task(server.serve())


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args))
    loop.run_forever()
