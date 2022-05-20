from sneakpeek.lib.settings import Settings, StorageType

from .base import Storage
from .in_memory_storage import InMemoryStorage


def get_storage(settings: Settings) -> Storage:
    if settings.storage_type == StorageType.IN_MEMORY:
        return InMemoryStorage.from_settings(settings)
    raise NotImplementedError(f"Unsupported storage type: {settings.storage_type}")
