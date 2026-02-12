from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

_meter = metrics.get_meter("tx-lookup-service")

API_REQUEST_LATENCY_SECONDS = _meter.create_histogram(
    name="api_request_latency_seconds",
    description="API request latency in seconds",
    unit="s",
)

API_REQUESTS_TOTAL = _meter.create_counter(
    name="api_requests_total",
    description="Total API requests",
)

API_REQUESTS_INFLIGHT = _meter.create_up_down_counter(
    name="api_requests_inflight",
    description="In-flight API requests",
)

DB_QUERY_LATENCY_SECONDS = _meter.create_histogram(
    name="db_query_latency_seconds",
    description="Database query latency in seconds",
    unit="s",
)

DB_QUERIES_TOTAL = _meter.create_counter(
    name="db_queries_total",
    description="Total database queries",
)


def observe_api_request(
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    attrs = {
        "method": method,
        "route": route,
        "status_code": str(status_code),
    }
    API_REQUEST_LATENCY_SECONDS.record(duration_seconds, attributes=attrs)
    API_REQUESTS_TOTAL.add(1, attributes=attrs)


# --- DB pool Observable Gauges ---

_pool_engine: list[Engine] = []  # populated by register_pool_engine()


def _pool_size_cb(options: CallbackOptions) -> Sequence[Observation]:
    if _pool_engine:
        return [Observation(_pool_engine[0].pool.size())]
    return []


def _pool_checked_out_cb(options: CallbackOptions) -> Sequence[Observation]:
    if _pool_engine:
        return [Observation(_pool_engine[0].pool.checkedout())]
    return []


def _pool_overflow_cb(options: CallbackOptions) -> Sequence[Observation]:
    if _pool_engine:
        return [Observation(_pool_engine[0].pool.overflow())]
    return []


def _pool_checked_in_cb(options: CallbackOptions) -> Sequence[Observation]:
    if _pool_engine:
        return [Observation(_pool_engine[0].pool.checkedin())]
    return []


DB_POOL_SIZE = _meter.create_observable_gauge(
    name="db_pool_size",
    description="Configured connection pool size",
    callbacks=[_pool_size_cb],
)

DB_POOL_CHECKED_OUT = _meter.create_observable_gauge(
    name="db_pool_checked_out",
    description="Number of connections currently checked out",
    callbacks=[_pool_checked_out_cb],
)

DB_POOL_OVERFLOW = _meter.create_observable_gauge(
    name="db_pool_overflow",
    description="Number of overflow connections currently open",
    callbacks=[_pool_overflow_cb],
)

DB_POOL_CHECKED_IN = _meter.create_observable_gauge(
    name="db_pool_checked_in",
    description="Number of connections available in pool",
    callbacks=[_pool_checked_in_cb],
)

DB_POOL_CHECKOUT_LATENCY_SECONDS = _meter.create_histogram(
    name="db_pool_checkout_latency_seconds",
    description="Time spent acquiring a connection from the pool",
    unit="s",
)


def register_pool_engine(engine: Engine) -> None:
    """Call once after engine creation to enable pool metric callbacks."""
    _pool_engine.clear()
    _pool_engine.append(engine)


def observe_db_query(
    operation: str,
    table: str,
    duration_seconds: float,
    success: bool,
) -> None:
    attrs = {
        "operation": operation,
        "table": table,
        "success": "true" if success else "false",
    }
    DB_QUERY_LATENCY_SECONDS.record(duration_seconds, attributes=attrs)
    DB_QUERIES_TOTAL.add(1, attributes=attrs)


__all__ = [
    "API_REQUESTS_INFLIGHT",
    "API_REQUESTS_TOTAL",
    "API_REQUEST_LATENCY_SECONDS",
    "DB_POOL_CHECKED_IN",
    "DB_POOL_CHECKED_OUT",
    "DB_POOL_CHECKOUT_LATENCY_SECONDS",
    "DB_POOL_OVERFLOW",
    "DB_POOL_SIZE",
    "DB_QUERIES_TOTAL",
    "DB_QUERY_LATENCY_SECONDS",
    "observe_api_request",
    "observe_db_query",
    "register_pool_engine",
]
