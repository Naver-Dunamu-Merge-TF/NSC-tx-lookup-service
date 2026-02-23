from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.common.config import AppConfig
from src.common.event_profiles import load_event_profiles


@dataclass(frozen=True)
class TopicProfile:
    ledger: str
    payment_order: str


@dataclass(frozen=True)
class AliasProfile:
    ledger: dict[str, tuple[str, ...]]
    payment_order: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class CoreRequiredPolicy:
    ledger: tuple[str, ...]
    payment_order: tuple[str, ...]


@dataclass(frozen=True)
class EventContractProfile:
    profile_id: str
    topics: TopicProfile
    aliases: AliasProfile
    core_required: CoreRequiredPolicy

    def topic_kind(self, topic: str) -> str | None:
        if topic == self.topics.ledger:
            return "ledger"
        if topic == self.topics.payment_order:
            return "payment_order"
        return None

    def aliases_for(self, topic_kind: str) -> dict[str, tuple[str, ...]]:
        if topic_kind == "ledger":
            return self.aliases.ledger
        if topic_kind == "payment_order":
            return self.aliases.payment_order
        raise ValueError(f"unsupported topic kind: {topic_kind}")

    def core_required_for(self, topic_kind: str) -> tuple[str, ...]:
        if topic_kind == "ledger":
            return self.core_required.ledger
        if topic_kind == "payment_order":
            return self.core_required.payment_order
        raise ValueError(f"unsupported topic kind: {topic_kind}")


def _to_alias_map(
    raw_aliases: Mapping[str, Any], profile_id: str, topic_kind: str
) -> dict[str, tuple[str, ...]]:
    aliases_raw = raw_aliases.get(topic_kind, {})
    if not isinstance(aliases_raw, Mapping):
        raise ValueError(f"{profile_id} aliases.{topic_kind} must be a mapping")

    canonical_map: dict[str, tuple[str, ...]] = {}
    for canonical_key_raw, alias_values_raw in aliases_raw.items():
        canonical_key = str(canonical_key_raw).strip()
        if not canonical_key:
            raise ValueError(f"{profile_id} aliases.{topic_kind} has empty canonical key")
        if not isinstance(alias_values_raw, tuple | list):
            raise ValueError(
                f"{profile_id} aliases.{topic_kind}.{canonical_key} must be a list"
            )
        values: list[str] = []
        for alias_value in alias_values_raw:
            alias = str(alias_value).strip()
            if not alias:
                raise ValueError(
                    f"{profile_id} aliases.{topic_kind}.{canonical_key} has empty alias"
                )
            if alias not in values:
                values.append(alias)
        if canonical_key not in values:
            values.insert(0, canonical_key)
        canonical_map[canonical_key] = tuple(values)
    return canonical_map


def _to_core_required(
    raw_required: Mapping[str, Any], profile_id: str, topic_kind: str
) -> tuple[str, ...]:
    required_raw = raw_required.get(topic_kind, [])
    if not isinstance(required_raw, tuple | list):
        raise ValueError(f"{profile_id} core_required.{topic_kind} must be a list")
    values: list[str] = []
    for raw_field in required_raw:
        field = str(raw_field).strip()
        if not field:
            raise ValueError(f"{profile_id} core_required.{topic_kind} has empty field")
        values.append(field)
    return tuple(values)


def load_event_contract_profile(config: AppConfig) -> EventContractProfile:
    profiles = load_event_profiles()
    profile_raw = profiles.get(config.event_profile_id)
    if profile_raw is None:
        raise ValueError(f"unknown event profile: {config.event_profile_id}")

    aliases_raw = profile_raw.get("aliases", {})
    if not isinstance(aliases_raw, Mapping):
        raise ValueError(f"{config.event_profile_id} aliases must be a mapping")

    core_required_raw = profile_raw.get("core_required", {})
    if not isinstance(core_required_raw, Mapping):
        raise ValueError(f"{config.event_profile_id} core_required must be a mapping")

    topics = TopicProfile(
        ledger=config.effective_ledger_topic,
        payment_order=config.effective_payment_order_topic,
    )
    if topics.ledger == topics.payment_order:
        raise ValueError(
            "effective ledger/payment topics must be distinct "
            f"(got {topics.ledger!r})"
        )

    return EventContractProfile(
        profile_id=config.event_profile_id,
        topics=topics,
        aliases=AliasProfile(
            ledger=_to_alias_map(aliases_raw, config.event_profile_id, "ledger"),
            payment_order=_to_alias_map(
                aliases_raw, config.event_profile_id, "payment_order"
            ),
        ),
        core_required=CoreRequiredPolicy(
            ledger=_to_core_required(
                core_required_raw, config.event_profile_id, "ledger"
            ),
            payment_order=_to_core_required(
                core_required_raw, config.event_profile_id, "payment_order"
            ),
        ),
    )
