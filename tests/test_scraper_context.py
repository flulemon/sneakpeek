from typing import Any
from unittest.mock import AsyncMock, call, patch

import aiohttp
import pytest

from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import (
    AfterResponsePlugin,
    BeforeRequestPlugin,
    Plugin,
    Request,
    ScraperContext,
)


class MockPlugin(BeforeRequestPlugin, AfterResponsePlugin):
    def __init__(self) -> None:
        self.before_request_mock = AsyncMock()
        self.after_response_mock = AsyncMock()

    @property
    def name(self) -> str:
        return "test"

    async def before_request(
        self,
        request: Request,
        config: Any | None = None,
    ) -> Request:
        await self.before_request_mock(request.url, config)
        return request

    async def after_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: Any | None = None,
    ) -> aiohttp.ClientResponse:
        await self.after_response_mock(request.url, config)
        return response


def context(
    plugins: list[Plugin] | None = None,
    plugins_configs: dict[str, Any] | None = None,
) -> ScraperContext:
    async def ping():
        pass

    return ScraperContext(
        ScraperConfig(plugins=plugins_configs),
        plugins=plugins,
        ping_session_func=ping,
    )


@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "options", "head"])
@pytest.mark.asyncio
async def test_http_methods(method: str):
    url = "test_url"
    headers = {"header1": "value1"}
    ctx = context()
    await ctx.start_session()
    with patch(
        f"aiohttp.ClientSession.{method}",
        new_callable=AsyncMock,
    ) as mocked_request:
        await getattr(ctx, method)(url, headers=headers)
        mocked_request.assert_called_once_with(url, headers=headers)


@pytest.mark.parametrize("max_concurrency", [-1, 0, 1])
@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "options", "head"])
@pytest.mark.asyncio
async def test_http_methods_multiple(method: str, max_concurrency: int):
    urls = [f"url{i}" for i in range(10)]
    headers = {"header1": "value1"}
    ctx = context()
    await ctx.start_session()
    with patch(
        f"aiohttp.ClientSession.{method}",
        new_callable=AsyncMock,
    ) as mocked_request:
        responses = await getattr(ctx, method)(
            urls,
            headers=headers,
            max_concurrency=max_concurrency,
        )
        assert len(responses) == len(
            urls
        ), f"Expected {len(urls)} responses but received {len(responses)}"
        mocked_request.assert_has_awaits(
            [call(url, headers=headers) for url in urls],
            any_order=True,
        )


@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "options", "head"])
@pytest.mark.asyncio
async def test_plugin_is_called(method: str):
    urls = [f"url{i}" for i in range(10)]
    headers = {"header1": "value1"}
    plugin = MockPlugin()
    plugin_config = {"config1": "value1"}
    ctx = context(
        plugins=[plugin],
        plugins_configs={plugin.name: plugin_config},
    )
    await ctx.start_session()
    with patch(
        f"aiohttp.ClientSession.{method}",
        new_callable=AsyncMock,
    ) as mocked_request:
        responses = await getattr(ctx, method)(urls, headers=headers)
        assert len(responses) == len(
            urls
        ), f"Expected {len(urls)} responses but received {len(responses)}"
        mocked_request.assert_has_awaits(
            [call(url, headers=headers) for url in urls],
            any_order=True,
        )
        plugin.before_request_mock.assert_has_awaits(
            [call(url, plugin_config) for url in urls],
            any_order=True,
        )
        plugin.after_response_mock.assert_has_awaits(
            [call(url, plugin_config) for url in urls],
            any_order=True,
        )


@pytest.mark.asyncio
async def test_invalid_plugin():
    class InvalidPlugin(BeforeRequestPlugin, AfterResponsePlugin):
        @property
        def name(self) -> str:
            return "not a python identifier"

        async def before_request(
            self, request: Request, config: Any | None = None
        ) -> Request:
            return request

        async def after_response(
            self,
            request: Request,
            response: aiohttp.ClientResponse,
            config: Any | None = None,
        ) -> aiohttp.ClientResponse:
            return response

    with pytest.raises(ValueError):
        ScraperContext(ScraperConfig(), plugins=[InvalidPlugin()])


def test_regex():
    text = '<tag param="value"><a href="to be found">some content</a></tag>'
    pattern = r'<a[^>]*href="(?P<href>[^"]+)'
    matches = context().regex(text, pattern)
    assert len(matches) == 1, "Expected to find a single match"
    match = matches[0]
    assert match.full_match == '<a href="to be found'
    assert match.groups == {"href": "to be found"}
