from __future__ import annotations

from opentelemetry import metrics

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
    "DB_QUERY_LATENCY_SECONDS",
    "DB_QUERIES_TOTAL",
    "observe_api_request",
    "observe_db_query",
]
