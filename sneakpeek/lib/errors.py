import fastapi_jsonrpc as jsonrpc


class ScraperNotFoundError(jsonrpc.BaseError):
    CODE = 5000
    MESSAGE = "Scraper not found"


class ScraperRunNotFoundError(jsonrpc.BaseError):
    CODE = 5001
    MESSAGE = "Scraper run not found"


class ScraperHasActiveRunError(jsonrpc.BaseError):
    CODE = 10000
    MESSAGE = "Scraper has active runs"


class ScraperRunPingNotStartedError(jsonrpc.BaseError):
    CODE = 10001
    MESSAGE = "Failed to ping not started scraper run"


class ScraperRunPingFinishedError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Tried to ping finished scraper run"


class UnknownScraperHandlerError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Tried to ping finished scraper run"
