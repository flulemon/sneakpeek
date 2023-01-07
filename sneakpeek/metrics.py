import asyncio
from functools import wraps

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


def measure_latency(subsystem: str):
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
                    error=e.__class__,
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
                    error=e.__class__,
                ).inc()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return wrapper
