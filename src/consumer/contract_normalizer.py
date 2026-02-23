from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.consumer.contract_profile import EventContractProfile
from src.consumer.events import EventValidationError

EVENT_TIME_REQUIRED_SENTINEL = "event_time_or_alias"


class UnsupportedTopicError(EventValidationError):
    pass


class ContractCoreViolationError(EventValidationError):
    pass


@dataclass(frozen=True)
class NormalizedPayload:
    payload: dict[str, Any]
    topic_kind: str
    alias_hits: tuple[tuple[str, str], ...]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and value.strip() == ""


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _resolve_alias_value(
    payload: Mapping[str, Any],
    aliases: tuple[str, ...],
    canonical_key: str,
    topic_kind: str,
    profile_id: str,
) -> tuple[str, Any] | None:
    candidates: list[tuple[str, Any]] = []
    for alias in aliases:
        raw_value = payload.get(alias)
        if _is_missing(raw_value):
            continue
        candidates.append((alias, _normalize_value(raw_value)))

    if not candidates:
        return None

    first_alias, first_value = candidates[0]
    for alias_name, alias_value in candidates[1:]:
        if alias_value != first_value:
            raise ContractCoreViolationError(
                "Alias conflict detected for "
                f"{topic_kind}.{canonical_key} in profile {profile_id}: "
                f"{first_alias}={first_value!r}, {alias_name}={alias_value!r}"
            )
    return first_alias, first_value


def _validate_core_required(
    normalized: Mapping[str, Any],
    topic_kind: str,
    required_fields: tuple[str, ...],
) -> None:
    missing_fields: list[str] = []
    for required in required_fields:
        key = "event_time" if required == EVENT_TIME_REQUIRED_SENTINEL else required
        if _is_missing(normalized.get(key)):
            missing_fields.append(required)
    if missing_fields:
        raise EventValidationError(
            f"Missing core required fields for {topic_kind}: {', '.join(missing_fields)}"
        )


def normalize_payload_for_topic(
    topic: str,
    payload: Mapping[str, Any],
    profile: EventContractProfile,
) -> NormalizedPayload:
    topic_kind = profile.topic_kind(topic)
    if topic_kind is None:
        raise UnsupportedTopicError(
            f"Unsupported topic {topic!r} for profile {profile.profile_id}"
        )

    normalized = dict(payload)
    alias_hits: list[tuple[str, str]] = []
    alias_map = profile.aliases_for(topic_kind)
    for canonical_key, aliases in alias_map.items():
        resolved = _resolve_alias_value(
            payload=payload,
            aliases=aliases,
            canonical_key=canonical_key,
            topic_kind=topic_kind,
            profile_id=profile.profile_id,
        )
        if resolved is None:
            continue
        alias_name, value = resolved
        normalized[canonical_key] = value
        if alias_name != canonical_key:
            alias_hits.append((canonical_key, alias_name))

    _validate_core_required(
        normalized=normalized,
        topic_kind=topic_kind,
        required_fields=profile.core_required_for(topic_kind),
    )
    return NormalizedPayload(
        payload=normalized,
        topic_kind=topic_kind,
        alias_hits=tuple(alias_hits),
    )
