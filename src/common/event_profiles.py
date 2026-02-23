from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

DEFAULT_EVENT_PROFILE_ID = "canonical-v1"
DEFAULT_TOPICS: dict[str, str] = {
    "ledger": "ledger.entry.upserted",
    "payment_order": "payment.order.upserted",
}
DEFAULT_EVENT_PROFILES_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "event_profiles.yaml"
)

_yaml_import_error: Exception | None = None
try:
    import yaml
except Exception as exc:  # pragma: no cover - import path failure only
    yaml = None
    _yaml_import_error = exc


def _expect_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return value


def _expect_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value.strip()


def _normalize_aliases(
    profile_id: str, aliases_raw: Mapping[str, Any]
) -> dict[str, dict[str, tuple[str, ...]]]:
    normalized: dict[str, dict[str, tuple[str, ...]]] = {}
    for topic_kind in ("ledger", "payment_order"):
        topic_aliases_raw = aliases_raw.get(topic_kind, {})
        topic_aliases = _expect_mapping(
            topic_aliases_raw, f"profiles.{profile_id}.aliases.{topic_kind}"
        )
        canonical_map: dict[str, tuple[str, ...]] = {}
        for canonical_key, aliases_raw_value in topic_aliases.items():
            canonical = _expect_text(
                canonical_key,
                f"profiles.{profile_id}.aliases.{topic_kind}.<canonical_key>",
            )
            if not isinstance(aliases_raw_value, list) or not aliases_raw_value:
                raise ValueError(
                    f"profiles.{profile_id}.aliases.{topic_kind}.{canonical} must be a non-empty list"
                )
            deduped: list[str] = []
            for alias_value in aliases_raw_value:
                alias = _expect_text(
                    alias_value,
                    f"profiles.{profile_id}.aliases.{topic_kind}.{canonical}[]",
                )
                if alias not in deduped:
                    deduped.append(alias)
            if canonical not in deduped:
                deduped.insert(0, canonical)
            canonical_map[canonical] = tuple(deduped)
        normalized[topic_kind] = canonical_map
    return normalized


def _normalize_core_required(
    profile_id: str, required_raw: Mapping[str, Any]
) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for topic_kind in ("ledger", "payment_order"):
        topic_required_raw = required_raw.get(topic_kind, [])
        if not isinstance(topic_required_raw, list):
            raise ValueError(
                f"profiles.{profile_id}.core_required.{topic_kind} must be a list"
            )
        values: list[str] = []
        for required_field in topic_required_raw:
            field_name = _expect_text(
                required_field,
                f"profiles.{profile_id}.core_required.{topic_kind}[]",
            )
            values.append(field_name)
        normalized[topic_kind] = tuple(values)
    return normalized


def _load_event_profiles_uncached(path: Path) -> dict[str, dict[str, Any]]:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to load event profiles; install PyYAML>=6.0"
        ) from _yaml_import_error

    if not path.exists():
        raise ValueError(f"event profile file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    root = _expect_mapping(loaded, "event profile root")
    version = root.get("version")
    if version != 1:
        raise ValueError(f"event profile version must be 1 (got {version!r})")

    profiles_raw = _expect_mapping(root.get("profiles"), "profiles")
    if not profiles_raw:
        raise ValueError("profiles must define at least one profile")

    profiles: dict[str, dict[str, Any]] = {}
    for profile_id_raw, profile_raw_value in profiles_raw.items():
        profile_id = _expect_text(profile_id_raw, "profile id")
        profile_raw = _expect_mapping(profile_raw_value, f"profiles.{profile_id}")

        topics_raw = _expect_mapping(profile_raw.get("topics"), f"profiles.{profile_id}.topics")
        topics = {
            "ledger": _expect_text(
                topics_raw.get("ledger"), f"profiles.{profile_id}.topics.ledger"
            ),
            "payment_order": _expect_text(
                topics_raw.get("payment_order"),
                f"profiles.{profile_id}.topics.payment_order",
            ),
        }
        aliases = _normalize_aliases(
            profile_id, _expect_mapping(profile_raw.get("aliases", {}), f"profiles.{profile_id}.aliases")
        )
        core_required = _normalize_core_required(
            profile_id,
            _expect_mapping(
                profile_raw.get("core_required", {}),
                f"profiles.{profile_id}.core_required",
            ),
        )

        profiles[profile_id] = {
            "topics": topics,
            "aliases": aliases,
            "core_required": core_required,
        }
    return profiles


@lru_cache(maxsize=8)
def _load_event_profiles_cached(path_key: str) -> dict[str, dict[str, Any]]:
    return _load_event_profiles_uncached(Path(path_key))


def load_event_profiles(path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    profile_path = Path(path) if path is not None else DEFAULT_EVENT_PROFILES_PATH
    return _load_event_profiles_cached(str(profile_path.resolve()))


def clear_event_profiles_cache() -> None:
    _load_event_profiles_cached.cache_clear()
