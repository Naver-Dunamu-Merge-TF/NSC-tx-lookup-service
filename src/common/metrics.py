from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest

API_LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.2,
    0.35,
    0.5,
    0.75,
    1.0,
    2.0,
    5.0,
)

DB_LATENCY_BUCKETS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.2,
    0.5,
    1.0,
    2.0,
    5.0,
)

API_REQUEST_LATENCY_SECONDS = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "route", "status_code"],
    buckets=API_LATENCY_BUCKETS,
)

API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "route", "status_code"],
)

API_REQUESTS_INFLIGHT = Gauge(
    "api_requests_inflight",
    "In-flight API requests",
    ["method", "route"],
)

DB_QUERY_LATENCY_SECONDS = Histogram(
    "db_query_latency_seconds",
    "Database query latency in seconds",
    ["operation", "table", "success"],
    buckets=DB_LATENCY_BUCKETS,
)

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table", "success"],
)


def observe_api_request(
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    labels = {
        "method": method,
        "route": route,
        "status_code": str(status_code),
    }
    API_REQUEST_LATENCY_SECONDS.labels(**labels).observe(duration_seconds)
    API_REQUESTS_TOTAL.labels(**labels).inc()


def observe_db_query(
    operation: str,
    table: str,
    duration_seconds: float,
    success: bool,
) -> None:
    labels = {
        "operation": operation,
        "table": table,
        "success": "true" if success else "false",
    }
    DB_QUERY_LATENCY_SECONDS.labels(**labels).observe(duration_seconds)
    DB_QUERIES_TOTAL.labels(**labels).inc()


def render_metrics() -> bytes:
    return generate_latest()


__all__ = [
    "API_REQUESTS_INFLIGHT",
    "API_REQUESTS_TOTAL",
    "API_REQUEST_LATENCY_SECONDS",
    "DB_QUERY_LATENCY_SECONDS",
    "DB_QUERIES_TOTAL",
    "CONTENT_TYPE_LATEST",
    "observe_api_request",
    "observe_db_query",
    "render_metrics",
]
