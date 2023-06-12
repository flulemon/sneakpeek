import os
from typing import Any
from unittest.mock import AsyncMock, call, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from typing_extensions import override

from sneakpeek.scraper.context import ScraperContext
from sneakpeek.scraper.model import (
    HttpMethod,
    Middleware,
    MiddlewareConfig,
    Request,
    ScraperConfig,
)


class MockMiddleware(Middleware):
    def __init__(self, name: str = "test") -> None:
        self._name = name
        self.on_request_mock = AsyncMock()
        self.on_response_mock = AsyncMock()

    @property
    def name(self) -> str:
        return self._name

    @override
    async def on_request(
        self,
        request: Request,
        config: MiddlewareConfig | None = None,
    ) -> Request:
        await self.on_request_mock(request.url, config)
        return request

    @override
    async def on_response(
        self,
        request: Request,
        response: aiohttp.ClientResponse,
        config: MiddlewareConfig | None = None,
    ) -> aiohttp.ClientResponse:
        await self.on_response_mock(request.url, config)
        return response


def context(
    middlewares: list[Middleware] | None = None,
    middleware_configs: dict[str, Any] | None = None,
) -> ScraperContext:
    return ScraperContext(
        ScraperConfig(middleware_config=middleware_configs),
        middlewares=middlewares,
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
    await ctx.close()


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
    await ctx.close()


@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "options", "head"])
@pytest.mark.asyncio
async def test_middleware_is_called_single_request(method: str):
    url = "url1"
    headers = {"header1": "value1"}
    middleware = MockMiddleware()
    middleware_config = {"config1": "value1"}
    ctx = context(
        middlewares=[middleware],
        middleware_configs={middleware.name: middleware_config},
    )
    await ctx.start_session()
    with patch(
        f"aiohttp.ClientSession.{method}",
        new_callable=AsyncMock,
    ) as mocked_request:
        await getattr(ctx, method)(url, headers=headers)
        mocked_request.assert_awaited_once_with(url, headers=headers)
        middleware.on_request_mock.assert_awaited_once_with(url, middleware_config)
        middleware.on_response_mock.assert_awaited_once_with(url, middleware_config)
    await ctx.close()


@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "options", "head"])
@pytest.mark.asyncio
async def test_middleware_is_called_multi_request(method: str):
    urls = [f"url{i}" for i in range(10)]
    headers = {"header1": "value1"}
    middleware = MockMiddleware()
    middleware_config = {"config1": "value1"}
    ctx = context(
        middlewares=[middleware],
        middleware_configs={middleware.name: middleware_config},
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
        middleware.on_request_mock.assert_has_awaits(
            [call(url, middleware_config) for url in urls],
            any_order=True,
        )
        middleware.on_response_mock.assert_has_awaits(
            [call(url, middleware_config) for url in urls],
            any_order=True,
        )
    await ctx.close()


@pytest.mark.asyncio
async def test_invalid_middleware():
    with pytest.raises(ValueError):
        ScraperContext(
            ScraperConfig(),
            middlewares=[MockMiddleware("not a python identifier")],
        )


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
            await ctx.close()


@pytest.mark.asyncio
async def test_download_file_with_file_path_specified():
    with aioresponses() as response:
        file_path = test_download_file_with_file_path_specified.__name__
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
            await ctx.close()


@pytest.mark.asyncio
async def test_download_file_with_process_fn():
    with aioresponses() as response:
        file_path = test_download_file_with_process_fn.__name__
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
            await ctx.close()


@pytest.mark.asyncio
async def test_download_multiple_files():
    with aioresponses() as response:
        concurrent_responses = 3
        urls = [
            f"{test_download_multiple_files.__name__}_url_{i}"
            for i in range(concurrent_responses)
        ]
        file_paths = [
            f"{test_download_multiple_files.__name__}_file_{i}"
            for i in range(concurrent_responses)
        ]
        responses = [
            f"{test_download_multiple_files.__name__}_resp_{i}"
            for i in range(concurrent_responses)
        ]

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
            await ctx.close()


@pytest.mark.asyncio
async def test_download_multiple_files_with_process_fn():
    with aioresponses() as response:
        concurrent_responses = 3
        urls = [
            f"{test_download_multiple_files_with_process_fn.__name__}_url_{i}"
            for i in range(concurrent_responses)
        ]
        file_paths = [
            f"{test_download_multiple_files_with_process_fn.__name__}_file_{i}"
            for i in range(concurrent_responses)
        ]
        responses = [
            f"{test_download_multiple_files_with_process_fn.__name__}_resp_{i}"
            for i in range(concurrent_responses)
        ]
        results = [
            f"{test_download_multiple_files_with_process_fn.__name__}_results_{i}"
            for i in range(concurrent_responses)
        ]
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
            await ctx.close()
