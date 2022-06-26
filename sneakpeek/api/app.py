import fastapi_jsonrpc as jsonrpc
import uvicorn

from sneakpeek.api.internal_api import get_internal_api_entrypoint
from sneakpeek.api.public_api import get_public_api_entrypoint
from sneakpeek.api.settings import Settings
from sneakpeek.lib.queue import Queue
from sneakpeek.lib.storage import get_storage

app = jsonrpc.API()
settings = Settings()
storage = get_storage(settings)
queue = Queue(storage)

app.bind_entrypoint(get_public_api_entrypoint(storage))
app.bind_entrypoint(get_internal_api_entrypoint(storage, queue))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
