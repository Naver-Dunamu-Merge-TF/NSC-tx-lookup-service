from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from prometheus_client import Counter, Gauge, Histogram

EVENT_LAG_BUCKETS = (
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
)

PAIR_AGE_BUCKETS = (
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
    900.0,
)

CONSUMER_MESSAGES_TOTAL = Counter(
    "consumer_messages_total",
    "Total consumer messages",
    ["topic", "status"],
)

CONSUMER_EVENT_LAG_SECONDS = Histogram(
    "consumer_event_lag_seconds",
    "Event time to processing lag in seconds",
    ["topic"],
    buckets=EVENT_LAG_BUCKETS,
)

CONSUMER_KAFKA_LAG = Gauge(
    "consumer_kafka_lag",
    "Kafka partition lag",
    ["topic", "partition"],
)

CONSUMER_FRESHNESS_SECONDS = Gauge(
    "consumer_freshness_seconds",
    "End-to-end data freshness in seconds (now - max event_time)",
    ["topic"],
)

CONSUMER_DLQ_TOTAL = Counter(
    "consumer_dlq_total",
    "Total DLQ writes",
    ["topic"],
)

VERSION_MISSING_TOTAL = Counter(
    "consumer_version_missing_total",
    "Events missing updated_at/source_version",
    ["topic"],
)

PAIR_TOTAL = Counter(
    "pairing_total",
    "Total pairing calculations",
)

PAIR_INCOMPLETE_TOTAL = Counter(
    "pairing_incomplete_total",
    "Incomplete pairing calculations",
)

PAIR_INCOMPLETE_AGE_SECONDS = Histogram(
    "pairing_incomplete_age_seconds",
    "Age of incomplete pairs in seconds",
    buckets=PAIR_AGE_BUCKETS,
)


def record_consumer_message(topic: str, status: str) -> None:
    CONSUMER_MESSAGES_TOTAL.labels(topic=topic, status=status).inc()


def record_event_lag(topic: str, event_time: datetime | None) -> None:
    if event_time is None:
        return
    now = datetime.now(timezone.utc)
    lag = (now - event_time).total_seconds()
    CONSUMER_EVENT_LAG_SECONDS.labels(topic=topic).observe(max(0.0, lag))


def record_kafka_lag(topic: str, partition: int, lag: int) -> None:
    CONSUMER_KAFKA_LAG.labels(topic=topic, partition=str(partition)).set(max(0, lag))


def record_dlq(topic: str) -> None:
    CONSUMER_DLQ_TOTAL.labels(topic=topic).inc()


def record_version_missing(topic: str, missing: bool) -> None:
    if missing:
        VERSION_MISSING_TOTAL.labels(topic=topic).inc()


@dataclass
class FreshnessTracker:
    last_event_time: dict[str, datetime] = field(default_factory=dict)

    def record(self, topic: str, event_time: datetime | None) -> None:
        if event_time is None:
            return
        last = self.last_event_time.get(topic)
        if last is None or event_time > last:
            self.last_event_time[topic] = event_time
        latest = self.last_event_time.get(topic)
        if latest is None:
            return
        now = datetime.now(timezone.utc)
        freshness = (now - latest).total_seconds()
        CONSUMER_FRESHNESS_SECONDS.labels(topic=topic).set(max(0.0, freshness))


@dataclass
class VersionMissingCounter:
    log_every: int = 100
    processed: int = 0
    missing_version: int = 0

    def record(self, missing: bool) -> bool:
        self.processed += 1
        if missing:
            self.missing_version += 1
        return self.processed % self.log_every == 0

    def summary(self) -> str:
        return (
            f"processed={self.processed} " f"version_missing_cnt={self.missing_version}"
        )


@dataclass
class PairingMetrics:
    log_every: int = 100
    total: int = 0
    incomplete: int = 0
    incomplete_age_sum: float = 0.0
    incomplete_age_max: float = 0.0

    def record(self, complete: bool, incomplete_age_sec: float | None) -> bool:
        self.total += 1
        PAIR_TOTAL.inc()
        if not complete:
            self.incomplete += 1
            PAIR_INCOMPLETE_TOTAL.inc()
            if incomplete_age_sec is not None:
                self.incomplete_age_sum += incomplete_age_sec
                self.incomplete_age_max = max(
                    self.incomplete_age_max, incomplete_age_sec
                )
                PAIR_INCOMPLETE_AGE_SECONDS.observe(incomplete_age_sec)
        return self.total % self.log_every == 0

    def summary(self) -> str:
        ratio = (self.incomplete / self.total) if self.total else 0.0
        avg_age = self.incomplete_age_sum / self.incomplete if self.incomplete else 0.0
        return (
            f"pair_total={self.total} "
            f"pair_incomplete={self.incomplete} "
            f"pair_incomplete_ratio={ratio:.4f} "
            f"pair_incomplete_avg_age_sec={avg_age:.2f} "
            f"pair_incomplete_max_age_sec={self.incomplete_age_max:.2f}"
        )
