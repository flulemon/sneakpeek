import inspect
import json
from typing import Any, Awaitable, Callable, Mapping

from pydantic import BaseModel
from typing_extensions import override

from sneakpeek.scraper.model import ScraperContextABC, ScraperHandler


class DynamicScraperParams(BaseModel):
    source_code: str
    args: list[Any] | None = None
    kwargs: Mapping[str, Any] | None = None


class DynamicScraperHandler(ScraperHandler):
    @property
    def name(self) -> str:
        return "dynamic_scraper"

    def compile(self, source_code: str) -> Callable[..., Awaitable[None]]:
        bytecode = compile(source=source_code, filename="<string>", mode="exec")
        session_globals = {}
        exec(bytecode, session_globals)
        if "context" in session_globals:
            raise SyntaxError("`context` is a reserved keyword")
        if "handler" not in session_globals:
            raise SyntaxError("Expected source code to define a `handler` function")
        handler = session_globals["handler"]
        if not inspect.iscoroutinefunction(handler):
            raise SyntaxError("Expected `handler` to be a function")
        if handler.__code__.co_argcount == 0:
            raise SyntaxError(
                "Expected `handler` to have at least one argument: `context: ScraperContext`"
            )
        return handler

    @override
    async def run(self, context: ScraperContextABC) -> str:
        params = DynamicScraperParams.parse_obj(context.params)
        handler = self.compile(params.source_code)
        result = await handler(context, *(params.args or []), **(params.kwargs or {}))
        if result is None:
            return "No result was returned"
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, indent=4)
        except TypeError as ex:
            return f"Failed to serialize result with error: {ex}"
