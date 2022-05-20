from enum import Enum

from pydantic import BaseSettings


class StorageType(str, Enum):
    IN_MEMORY = "in_memory"


class Settings(BaseSettings):
    storage_type: StorageType = StorageType.IN_MEMORY

    class Config:
        use_enum_values = True
