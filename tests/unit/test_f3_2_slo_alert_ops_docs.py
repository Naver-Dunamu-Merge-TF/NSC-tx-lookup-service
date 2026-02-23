from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ALERT_RULES_PATH = ROOT / "docker" / "observability" / "alert_rules.yml"
RUNBOOK_PATH = ROOT / "docs" / "ops" / "f3_2_slo_alerts_runbook.md"
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_rule_names() -> list[str]:
    with ALERT_RULES_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return [str(rule["name"]) for rule in data["rules"]]


def _extract_f3_2_section(text: str) -> str:
    match = re.search(
        r"#### 대형 태스크 F3-2: SLO 알림 규칙 운영 적용(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "F3-2 section not found in roadmap"
    return match.group("section")


def test_runbook_exists() -> None:
    assert RUNBOOK_PATH.exists(), f"Missing runbook: {RUNBOOK_PATH}"


def test_runbook_covers_all_alert_rules() -> None:
    runbook = _read(RUNBOOK_PATH)
    for rule_name in _load_rule_names():
        assert f"`{rule_name}`" in runbook, f"runbook missing rule: {rule_name}"


def test_runbook_contains_required_metric_groups() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "api_request_latency_seconds",
        "consumer_freshness_seconds",
        "db_pool_size",
        "db_pool_checked_out",
        "db_pool_overflow",
        "db_pool_checked_in",
        "db_pool_checkout_latency_seconds",
        "db_replication_lag_seconds",
        "03_dashboard_api_latency.log",
        "04_dashboard_consumer_freshness.log",
        "05_dashboard_db_pool.log",
        "06_dashboard_db_replication.log",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_decisions_doc_has_f3_2_decisions() -> None:
    decisions = _read(DECISIONS_PATH)
    required_tokens = (
        "### DEC-232",
        "### DEC-233",
        "### DEC-234",
    )
    for token in required_tokens:
        assert token in decisions, f"missing decision token: {token}"


def test_roadmap_f3_2_has_evidence_link_token() -> None:
    section = _extract_f3_2_section(_read(ROADMAP_PATH))
    assert section.count("- [x]") >= 4
    assert ".agents/logs/verification/" in section
    assert "f3_2_slo_alert_ops" in section
