import fastapi_jsonrpc as jsonrpc


class ScraperNotFoundError(jsonrpc.BaseError):
    CODE = 5000
    MESSAGE = "Scraper not found"


class ScraperJobNotFoundError(jsonrpc.BaseError):
    CODE = 5001
    MESSAGE = "Scraper job not found"


class ScraperHasActiveRunError(jsonrpc.BaseError):
    CODE = 10000
    MESSAGE = "Scraper has active jobs"


class ScraperJobPingNotStartedError(jsonrpc.BaseError):
    CODE = 10001
    MESSAGE = "Failed to ping not started scraper job"


class ScraperJobPingFinishedError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Tried to ping finished scraper job"


class ScraperJobTimedOut(jsonrpc.BaseError):
    CODE = 10003
    MESSAGE = "Scraper job has timed out"


class UnknownScraperHandlerError(jsonrpc.BaseError):
    CODE = 10002
    MESSAGE = "Unknown scraper handler"
