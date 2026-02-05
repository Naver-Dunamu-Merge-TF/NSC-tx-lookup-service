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
