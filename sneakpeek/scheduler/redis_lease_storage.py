from datetime import datetime, timedelta

from redis.asyncio import Redis

from sneakpeek.metrics import count_invocations, measure_latency
from sneakpeek.scheduler.model import Lease, LeaseStorageABC


class RedisLeaseStorage(LeaseStorageABC):
    """Redis storage for leases. Should only be used for development purposes"""

    def __init__(self, redis: Redis) -> None:
        """
        Args:
            redis (Redis): Async redis client
        """
        self._redis = redis

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def maybe_acquire_lease(
        self,
        lease_name: str,
        owner_id: str,
        acquire_for: timedelta,
    ) -> Lease | None:
        lease_key = f"lease:{lease_name}"
        existing_lease = await self._redis.get(lease_key)
        result = None
        if not existing_lease or existing_lease.decode() == owner_id:
            result = await self._redis.set(
                f"lease:{lease_name}",
                owner_id,
                ex=acquire_for,
            )
        return (
            Lease(
                name=lease_name,
                owner_id=owner_id,
                acquired=datetime.utcnow(),
                acquired_until=datetime.utcnow() + acquire_for,
            )
            if result
            else None
        )

    @count_invocations(subsystem="storage")
    @measure_latency(subsystem="storage")
    async def release_lease(self, lease_name: str, owner_id: str) -> None:
        lease_owner = await self._redis.get(f"lease:{lease_name}")
        if lease_owner == owner_id:
            await self._redis.delete(f"lease:{lease_name}")
