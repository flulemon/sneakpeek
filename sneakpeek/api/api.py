import fastapi_jsonrpc as jsonrpc

from sneakpeek.api.internal_api import get_internal_api_entrypoint
from sneakpeek.api.public_api import get_public_api_entrypoint
from sneakpeek.lib.queue import QueueABC
from sneakpeek.lib.storage.base import Storage


def create_api(storage: Storage, queue: QueueABC) -> jsonrpc.API:
    app = jsonrpc.API()
    app.bind_entrypoint(get_public_api_entrypoint(storage))
    app.bind_entrypoint(get_internal_api_entrypoint(storage, queue))
    return app
