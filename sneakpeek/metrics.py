import asyncio
from functools import wraps
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

invocations_counter = Counter(
    name="invocations",
    documentation="Methods invocations counter",
    namespace="sneakpeek",
    labelnames=["subsystem", "method", "type", "error"],
)
latency_histogram = Histogram(
    name="latency",
    documentation="Time spent processing method",
    namespace="sneakpeek",
    labelnames=["subsystem", "method"],
)
delay_histogram = Histogram(
    name="delay",
    documentation="Execution and scheduling delay",
    namespace="sneakpeek",
    labelnames=["type"],
)
replicas_gauge = Gauge(
    name="replicas",
    documentation="Number of active subsytem replicas",
    namespace="sneakpeek",
    labelnames=["type"],
)


def _get_full_class_name(obj: Any) -> str:
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + "." + obj.__class__.__name__


def measure_latency(subsystem: str):
    """
    Decorator for measuring latency of the function (works for both sync and async functions).

    .. code-block:: python3

        @measure_latency(subsytem="my subsystem")
        def my_awesome_func():
            ...


    This will export following Prometheus histogram metric:


    .. code-block::

        sneakpeek_latency{subsystem="my subsystem", method="my_awesome_func"}

    Args:
        subsystem (str): Subsystem name to be used in the metric annotation
    """

    def wrapper(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with latency_histogram.labels(
                subsystem=subsystem, method=func.__name__
            ).time():
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with latency_histogram.labels(
                subsystem=subsystem, method=func.__name__
            ).time():
                return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return wrapper


def count_invocations(subsystem: str):
    """
    Decorator for measuring number of function invocations (works for both sync and async functions).

    .. code-block:: python3

        @count_invocations(subsytem="my subsystem")
        def my_awesome_func():
            ...


    This will export following Prometheus counter metrics:


    .. code-block::

        # Total number of invocations
        sneakpeek_invocations{subsystem="my subsystem", method="my_awesome_func", type="total", error=""}
        # Total number of successful invocations (ones that haven't thrown an exception)
        sneakpeek_invocations{subsystem="my subsystem", method="my_awesome_func", type="success", error=""}
        # Total number of failed invocations (ones that have thrown an exception)
        sneakpeek_invocations{subsystem="my subsystem", method="my_awesome_func", type="error", error="<Exception class name>"}

    Args:
        subsystem (str): Subsystem name to be used in the metric annotation
    """

    def wrapper(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            invocations_counter.labels(
                subsystem=subsystem,
                method=func.__name__,
                type="total",
                error="",
            ).inc()
            try:
                result = func(*args, **kwargs)
                invocations_counter.labels(
                    subsystem=subsystem,
                    method=func.__name__,
                    type="success",
                    error="",
                ).inc()
                return result
            except Exception as e:
                invocations_counter.labels(
                    subsystem=subsystem,
                    method=func.__name__,
                    type="error",
                    error=_get_full_class_name(e),
                ).inc()
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            invocations_counter.labels(
                subsystem=subsystem,
                method=func.__name__,
                type="total",
                error="",
            ).inc()
            try:
                result = await func(*args, **kwargs)
                invocations_counter.labels(
                    subsystem=subsystem,
                    method=func.__name__,
                    type="success",
                    error="",
                ).inc()
                return result
            except Exception as e:
                invocations_counter.labels(
                    subsystem=subsystem,
                    method=func.__name__,
                    type="error",
                    error=_get_full_class_name(e),
                ).inc()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return wrapper
