import os
from typing import Any
from unittest.mock import AsyncMock, call, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from sneakpeek.scraper_config import ScraperConfig
from sneakpeek.scraper_context import (
    AfterResponsePlugin,
    BeforeRequestPlugin,
    HttpMethod,
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


@pytest.mark.asyncio
async def test_download_file_with_no_file_path_specified():
    with aioresponses() as response:
        file_path = None
        try:
            url = "test_url"
            body = "test body"
            response.get(url, status=200, body=body)

            ctx = context()
            await ctx.start_session()
            file_path = await ctx.download_file(HttpMethod.GET, url)
            assert file_path is not None, "Expected file path to be generated"
            assert os.path.exists(file_path), f"Expected file {file_path} to be present"
            with open(file_path, "r") as f:
                contents = f.read()
                assert contents == body, f"Expected downloaded file to have '{body}'"
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)


@pytest.mark.asyncio
async def test_download_file_with_file_path_specified():
    with aioresponses() as response:
        file_path = "tmp_test_file_path"
        try:
            url = "test_url"
            body = "test body"
            response.get(url, status=200, body=body)

            ctx = context()
            await ctx.start_session()
            actual_file_path = await ctx.download_file(
                HttpMethod.GET, url, file_path=file_path
            )
            assert (
                actual_file_path == file_path
            ), f"Expected to receive original file path {file_path}"
            assert os.path.exists(file_path), f"Expected file {file_path} to be present"
            with open(file_path, "r") as f:
                contents = f.read()
                assert contents == body, f"Expected downloaded file to have '{body}'"
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)


@pytest.mark.asyncio
async def test_download_file_with_process_fn():
    with aioresponses() as response:
        file_path = "tmp_test_file_path"
        try:
            url = "test_url"
            body = "test body"
            expected_process_result = "return"
            response.get(url, status=200, body=body)
            process_fn = AsyncMock(return_value=expected_process_result)

            ctx = context()
            await ctx.start_session()
            actual_process_result = await ctx.download_file(
                HttpMethod.GET,
                url,
                file_path=file_path,
                file_process_fn=process_fn,
            )
            assert (
                actual_process_result == expected_process_result
            ), f"Expected to receive return value of the process function: '{expected_process_result}'"
            assert not os.path.exists(
                file_path
            ), f"Expected file '{file_path}' to be deleted after processing. But it's still present"
            process_fn.assert_awaited_once_with(file_path)
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)


@pytest.mark.asyncio
async def test_download_multiple_files():
    with aioresponses() as response:
        urls = ["url1", "url2", "url3"]
        file_paths = ["file1", "file2", "file3"]
        responses = ["body1", "body2", "body3"]

        for url, resp in zip(urls, responses):
            response.get(url, status=200, body=resp)

        try:
            ctx = context()
            await ctx.start_session()
            actual_file_paths = await ctx.download_files(
                HttpMethod.GET, urls, file_paths=file_paths
            )
            assert (
                actual_file_paths == file_paths
            ), f"Expected to receive original file paths {file_paths}"
            for actual_file_path, expected_response in zip(
                actual_file_paths, responses
            ):
                assert os.path.exists(
                    actual_file_path
                ), f"Expected file {actual_file_path} to be present"
                with open(actual_file_path, "r") as f:
                    contents = f.read()
                    assert (
                        contents == expected_response
                    ), f"Expected downloaded file to have '{expected_response}'"
        finally:
            for file_path in file_paths:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)


@pytest.mark.asyncio
async def test_download_multiple_files_with_process_fn():
    with aioresponses() as response:
        urls = ["url1", "url2", "url3"]
        file_paths = ["file1", "file2", "file3"]
        responses = ["body1", "body2", "body3"]
        results = ["result1", "result2", "result3"]
        process_fn = AsyncMock(side_effect=results)

        for url, resp in zip(urls, responses):
            response.get(url, status=200, body=resp)

        try:
            ctx = context()
            await ctx.start_session()
            actual_results = await ctx.download_files(
                HttpMethod.GET,
                urls,
                file_paths=file_paths,
                file_process_fn=process_fn,
            )
            assert (
                actual_results == results
            ), f"Expected to receive process function results {results}"

            for path in file_paths:
                assert not os.path.exists(
                    path
                ), f"Expected file '{path}' to be removed after processing"

            process_fn.assert_has_awaits(
                [call(path) for path in file_paths], any_order=True
            )

        finally:
            for file_path in file_paths:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
