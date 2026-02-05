from __future__ import annotations

from dataclasses import dataclass


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
            f"processed={self.processed} "
            f"version_missing_cnt={self.missing_version}"
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
        if not complete:
            self.incomplete += 1
            if incomplete_age_sec is not None:
                self.incomplete_age_sum += incomplete_age_sec
                self.incomplete_age_max = max(self.incomplete_age_max, incomplete_age_sec)
        return self.total % self.log_every == 0

    def summary(self) -> str:
        ratio = (self.incomplete / self.total) if self.total else 0.0
        avg_age = (
            self.incomplete_age_sum / self.incomplete
            if self.incomplete
            else 0.0
        )
        return (
            f"pair_total={self.total} "
            f"pair_incomplete={self.incomplete} "
            f"pair_incomplete_ratio={ratio:.4f} "
            f"pair_incomplete_avg_age_sec={avg_age:.2f} "
            f"pair_incomplete_max_age_sec={self.incomplete_age_max:.2f}"
        )
