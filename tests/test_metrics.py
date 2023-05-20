import pytest
from prometheus_client import REGISTRY

from sneakpeek.metrics import count_invocations, measure_latency

SUBSYSTEM = "test"

exception_to_raise = ValueError()
exception_to_raise_name = ValueError.__name__


@count_invocations(SUBSYSTEM)
@measure_latency(SUBSYSTEM)
async def async_test_fn(fail: bool = False):
    if fail:
        raise exception_to_raise
    return 1


@count_invocations(SUBSYSTEM)
@measure_latency(SUBSYSTEM)
def sync_test_fn(fail: bool = False):
    if fail:
        raise exception_to_raise
    return 1


latency_labels_sync = {
    "subsystem": SUBSYSTEM,
    "method": sync_test_fn.__name__,
}
latency_labels_async = {
    "subsystem": SUBSYSTEM,
    "method": async_test_fn.__name__,
}


def invocation_labels_sync(type: str, error: str = ""):
    return {
        "subsystem": SUBSYSTEM,
        "method": sync_test_fn.__name__,
        "type": type,
        "error": error,
    }


def invocation_labels_async(type: str, error: str = ""):
    return {
        "subsystem": SUBSYSTEM,
        "method": async_test_fn.__name__,
        "type": type,
        "error": error,
    }


@pytest.mark.asyncio
async def test_measure_latency_async():
    before = REGISTRY.get_sample_value("sneakpeek_latency_count", latency_labels_async)
    await async_test_fn()
    after = REGISTRY.get_sample_value("sneakpeek_latency_count", latency_labels_async)
    assert after - (before or 0) == 1


@pytest.mark.asyncio
async def test_measure_latency_sync():
    before = REGISTRY.get_sample_value("sneakpeek_latency_count", latency_labels_sync)
    sync_test_fn()
    after = REGISTRY.get_sample_value("sneakpeek_latency_count", latency_labels_sync)
    assert after - (before or 0) == 1


@pytest.mark.asyncio
async def test_count_invocations_async():
    before_total = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("total"),
    )
    before_success = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("success"),
    )
    before_error = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("error", exception_to_raise_name),
    )
    await async_test_fn(fail=False)
    with pytest.raises(type(exception_to_raise)):
        await async_test_fn(fail=True)

    after_total = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("total"),
    )
    after_success = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("success"),
    )
    after_error = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_async("error", exception_to_raise_name),
    )
    assert after_total - (before_total or 0) == 2
    assert after_success - (before_success or 0) == 1
    assert after_error - (before_error or 0) == 1


def test_count_invocations_sync():
    before_total = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("total"),
    )
    before_success = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("success"),
    )
    before_error = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("error", exception_to_raise_name),
    )
    sync_test_fn(fail=False)
    with pytest.raises(type(exception_to_raise)):
        sync_test_fn(fail=True)

    after_total = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("total"),
    )
    after_success = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("success"),
    )
    after_error = REGISTRY.get_sample_value(
        "sneakpeek_invocations_total",
        invocation_labels_sync("error", exception_to_raise_name),
    )
    assert after_total - (before_total or 0) == 2
    assert after_success - (before_success or 0) == 1
    assert after_error - (before_error or 0) == 1
