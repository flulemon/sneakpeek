import logging
from asyncio import Lock
from datetime import datetime, timedelta

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.scheduler.model import Lease, LeaseStorageABC


class InMemoryLeaseStorage(LeaseStorageABC):
    """In memory storage for leases. Should only be used for development purposes"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._lock = Lock()
        self._leases: dict[str, Lease] = {}

    def _can_acquire_lease(self, lease_name: str, owner_id: str) -> bool:
        existing_lease = self._leases.get(lease_name)
        return (
            not existing_lease
            or existing_lease.acquired_until < datetime.utcnow()
            or existing_lease.owner_id == owner_id
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        async with self._lock:
            if self._can_acquire_lease(lease_name, owner_id):
                self._leases[lease_name] = Lease(
                    name=lease_name,
                    owner_id=owner_id,
                    acquired=datetime.utcnow(),
                    acquired_until=datetime.utcnow() + acquire_for,
                )
                return self._leases[lease_name]
        return None

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        async with self._lock:
            if lease_name not in self._leases:
                return
            if self._can_acquire_lease(lease_name, owner_id):
                del self._leases[lease_name]
