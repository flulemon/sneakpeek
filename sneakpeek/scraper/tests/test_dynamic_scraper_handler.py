import inspect
from unittest.mock import AsyncMock, call

import pytest

from sneakpeek.scraper.dynamic_scraper_handler import (
    DynamicScraperHandler,
    DynamicScraperParams,
)


class FakeScraperContext:
    def __init__(self, params: DynamicScraperParams) -> None:
        self.params = params.dict()
        self.get_mock = AsyncMock()

    async def get(self, url: str) -> str:
        return await self.get_mock(url)


@pytest.fixture
def handler() -> DynamicScraperHandler:
    yield DynamicScraperHandler()


SOURCE_CODE_NO_HANDLER_DEFINED = """
from sneakpeek.scraper.context import ScraperContext

async def handler_not_defined(context: ScraperContext) -> str:
    return "1"
"""


def test_Given_SourceCodeHasNoHandlerDefined_When_Compiled_Then_SyntaxErrorIsThrown(
    handler: DynamicScraperHandler,
) -> None:
    with pytest.raises(SyntaxError):
        handler.compile(SOURCE_CODE_NO_HANDLER_DEFINED)


SOURCE_CODE_HANDLER_NOT_ASYNC = """
from sneakpeek.scraper.context import ScraperContext

def handler(context: ScraperContext) -> str:
    return "1"
"""


def test_Given_SourceCodeWithSyncHandler_When_Compiled_Then_SyntaxErrorIsThrown(
    handler: DynamicScraperHandler,
) -> None:
    with pytest.raises(SyntaxError):
        handler.compile(SOURCE_CODE_HANDLER_NOT_ASYNC)


SOURCE_CODE_HANDLER_OBJECT = """
handler = 1
"""
SOURCE_CODE_HANDLER_CLASS = """
class handler:
    pass
"""


def test_Given_SourceCodeWithHandlerNotFunction_When_Compiled_Then_SyntaxErrorIsThrown(
    handler: DynamicScraperHandler,
) -> None:
    with pytest.raises(SyntaxError):
        handler.compile(SOURCE_CODE_HANDLER_OBJECT)
    with pytest.raises(SyntaxError):
        handler.compile(SOURCE_CODE_HANDLER_CLASS)


SOURCE_CODE_HANDLER_NO_ARGS = """
async def handler():
    return "1"
"""


def test_Given_SourceCodeWithHandleWithNoArgs_When_Compiled_Then_SyntaxErrorIsThrown(
    handler: DynamicScraperHandler,
) -> None:
    with pytest.raises(SyntaxError):
        handler.compile(SOURCE_CODE_HANDLER_NO_ARGS)


SOURCE_CODE_COMPILES = """
from sneakpeek.scraper.context import ScraperContext

async def handler(ctx: ScraperContext) -> str:
    return "1"
"""


def test_Given_SourceCode_When_Compiled_Then_AsyncFunctionIsReturned(
    handler: DynamicScraperHandler,
) -> None:
    func = handler.compile(SOURCE_CODE_COMPILES)
    assert inspect.iscoroutinefunction(func)
    assert func.__code__.co_argcount == 1


CUSTOM_SOURCE_CODE = """
from sneakpeek.scraper.context import ScraperContext

async def handler(ctx: ScraperContext, param1: str, param2: str = "test2", result="123"):
    for param in [param1, param2]:
        await ctx.get(param)
    return result
"""


@pytest.mark.asyncio
async def test_Given_CustomCode_When_RanByHandler_Then_ContextIsCalled(
    handler: DynamicScraperHandler,
) -> None:
    context = FakeScraperContext(
        DynamicScraperParams(
            source_code=CUSTOM_SOURCE_CODE,
            args=["url1"],
            kwargs={"param2": "url2", "result": "some_result"},
        ),
    )
    result = await handler.run(context)
    assert result == "some_result"
    context.get_mock.assert_has_awaits(
        [
            call("url1"),
            call("url2"),
        ]
    )
