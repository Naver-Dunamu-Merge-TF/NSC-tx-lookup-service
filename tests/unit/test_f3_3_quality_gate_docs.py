from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = ROOT / "docs" / "ops" / "f3_3_quality_gate_runbook.md"
SCENARIOS_PATH = ROOT / "docs" / "ops" / "f3_3_l3_cluster_smoke_scenarios.md"
EVIDENCE_TEMPLATE_PATH = (
    ROOT / "docs" / "ops" / "f3_3_validation_evidence_template.md"
)
INFRA_INVENTORY_PATH = ROOT / ".specs" / "infra" / "tx_lookup_azure_resource_inventory.md"
CHECKLIST_PATH = ROOT / "docs" / "ops" / "f3_3_closeout_checklist.md"
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_f3_3_section(text: str) -> str:
    import re

    match = re.search(
        r"#### 대형 태스크 F3-3: 품질 게이트 마감(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "F3-3 section not found in roadmap"
    return match.group("section")


def test_runbook_exists() -> None:
    assert RUNBOOK_PATH.exists(), f"Missing runbook: {RUNBOOK_PATH}"


def test_runbook_contains_l2_command() -> None:
    runbook = _read(RUNBOOK_PATH)
    assert ".venv/bin/python -m pytest --cov-fail-under=80" in runbook


def test_runbook_contains_l3_in_cluster_requirement() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "in-cluster",
        "AKS",
        "E2",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_runbook_contains_evidence_path_policy() -> None:
    runbook = _read(RUNBOOK_PATH)
    assert ".agents/logs/verification/" in runbook


def test_l3_smoke_scenario_spec_exists() -> None:
    assert SCENARIOS_PATH.exists(), f"Missing scenario spec: {SCENARIOS_PATH}"


def test_l3_smoke_scenario_spec_contains_required_scenarios() -> None:
    scenarios = _read(SCENARIOS_PATH)
    required_tokens = (
        "L3-SMOKE-01",
        "/admin/tx/{tx_id}",
        "returns `200`",
        "L3-SMOKE-02",
        "returns `404`",
        "L3-SMOKE-03",
        "pairing_status",
        "incomplete",
        "L3-SMOKE-04",
        "status-change",
        "freshness",
    )
    for token in required_tokens:
        assert token in scenarios, f"scenario spec missing token: {token}"


def test_runbook_references_l3_scenario_spec() -> None:
    runbook = _read(RUNBOOK_PATH)
    assert "docs/ops/f3_3_l3_cluster_smoke_scenarios.md" in runbook


def test_runbook_contains_aks_readiness_and_minimum_evidence_policy() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "provisioningState",
        "namespace readiness",
        "minimum evidence",
        "successful in-cluster run",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_validation_evidence_template_exists_and_has_command_capture_format() -> None:
    assert EVIDENCE_TEMPLATE_PATH.exists(), (
        f"Missing evidence template: {EVIDENCE_TEMPLATE_PATH}"
    )
    template = _read(EVIDENCE_TEMPLATE_PATH)
    required_tokens = (
        "`command`",
        "`exit_code`",
        "UTC timestamp",
        "AKS readiness",
        "minimum evidence set",
    )
    for token in required_tokens:
        assert token in template, f"evidence template missing token: {token}"


def test_infra_inventory_references_f3_3_evidence_contract() -> None:
    infra = _read(INFRA_INVENTORY_PATH)
    required_tokens = (
        "f3_3_quality_gate_runbook.md",
        "f3_3_validation_evidence_template.md",
        "provisioningState=Succeeded",
        "txlookup namespace ready",
    )
    for token in required_tokens:
        assert token in infra, f"infra inventory missing token: {token}"


def test_f3_3_closeout_checklist_exists_with_required_sections() -> None:
    assert CHECKLIST_PATH.exists(), f"Missing checklist: {CHECKLIST_PATH}"
    checklist = _read(CHECKLIST_PATH)
    required_tokens = (
        "Contract evidence",
        "F3-1",
        "Alerts evidence",
        "F3-2",
        "Test evidence",
        "F3-3",
        "L2",
        "L3",
        "owner",
        "date",
        "result",
        "go/no-go",
    )
    for token in required_tokens:
        assert token in checklist, f"checklist missing token: {token}"


def test_f3_3_checklist_links_key_artifacts() -> None:
    checklist = _read(CHECKLIST_PATH)
    required_tokens = (
        "configs/topic_checklist.md",
        "docs/ops/f3_2_slo_alerts_runbook.md",
        "docs/ops/f3_3_quality_gate_runbook.md",
        "docs/ops/f3_3_l3_cluster_smoke_scenarios.md",
        "docs/ops/f3_3_validation_evidence_template.md",
    )
    for token in required_tokens:
        assert token in checklist, f"checklist missing artifact link: {token}"


def test_roadmap_f3_3_section_references_closeout_docs() -> None:
    section = _extract_f3_3_section(_read(ROADMAP_PATH))
    required_tokens = (
        "docs/ops/f3_3_quality_gate_runbook.md",
        "docs/ops/f3_3_l3_cluster_smoke_scenarios.md",
        "docs/ops/f3_3_closeout_checklist.md",
    )
    for token in required_tokens:
        assert token in section, f"roadmap F3-3 missing token: {token}"


def test_decisions_doc_contains_f3_3_conditional_policy_entry() -> None:
    decisions = _read(DECISIONS_PATH)
    required_tokens = (
        "### DEC-235",
        "CONDITIONAL (L3 deferred by DEC-226)",
        "F3-3 closeout checklist",
        "retry date",
    )
    for token in required_tokens:
        assert token in decisions, f"decisions missing token: {token}"
