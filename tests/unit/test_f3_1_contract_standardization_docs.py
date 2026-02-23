from __future__ import annotations

import re
from pathlib import Path

from src.api.service import _resolve_status_group

ROOT = Path(__file__).resolve().parents[2]
TOPIC_CHECKLIST = ROOT / "configs" / "topic_checklist.md"
DECISIONS_DOC = ROOT / ".specs" / "decision_open_items.md"
ROADMAP_DOC = ROOT / ".roadmap" / "implementation_roadmap.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_f3_1_section(text: str) -> str:
    match = re.search(
        r"#### 대형 태스크 F3-1: 상태/버전 이벤트 계약 표준화(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "F3-1 section not found in roadmap"
    return match.group("section")


def test_status_mapping_table_matches_api_behavior() -> None:
    text = _read(TOPIC_CHECKLIST)
    rows = re.findall(
        r"^\|\s*`?(SUCCESS|FAIL|IN_PROGRESS|UNKNOWN)`?\s*\|\s*(.+?)\s*\|$",
        text,
        re.M,
    )
    assert rows, "status_group mapping table rows not found"

    for group, value_cell in rows:
        statuses = re.findall(r"`([^`]+)`", value_cell)
        if group == "UNKNOWN":
            continue
        assert statuses, f"{group} row must define at least one status token"
        for status in statuses:
            assert _resolve_status_group(status) == group

    assert _resolve_status_group("F3_1_UNKNOWN_STATUS") == "UNKNOWN"
    assert _resolve_status_group(None) == "UNKNOWN"


def test_f3_1_thresholds_and_dec_references_are_documented() -> None:
    checklist = _read(TOPIC_CHECKLIST)
    decisions = _read(DECISIONS_DOC)

    checklist_required_tokens = (
        "metadata_coverage_ratio(topic)",
        ">= 0.99",
        "core_violation_rate",
        "<= 0.001",
        "alias_hit_ratio",
        "<= 0.40",
        "version_missing_ratio",
        "<= 0.05",
        "DEC-229",
        "DEC-230",
        "DEC-231",
    )
    for token in checklist_required_tokens:
        assert token in checklist, f"missing checklist token: {token}"

    decisions_required_tokens = (
        "### DEC-229",
        "### DEC-230",
        "### DEC-231",
        ">= 0.99",
        "<= 0.001",
        "<= 0.40",
        "<= 0.05",
    )
    for token in decisions_required_tokens:
        assert token in decisions, f"missing decision token: {token}"


def test_roadmap_f3_1_has_completion_and_evidence_links() -> None:
    section = _extract_f3_1_section(_read(ROADMAP_DOC))

    assert section.count("- [x]") >= 5
    assert ".specs/decision_open_items.md" in section
    assert "configs/topic_checklist.md" in section
    assert ".specs/upstream_event_contract_handoff_log.md" in section
    assert ".agents/logs/verification/" in section
    assert "TBD_f3_1_contract_standardization" not in section
