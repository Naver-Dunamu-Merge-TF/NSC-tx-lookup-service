from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"
INFRA_INVENTORY_PATH = ROOT / ".specs" / "infra" / "tx_lookup_azure_resource_inventory.md"

RUNBOOK_PATH = ROOT / "docs" / "ops" / "e2_3_reload_cutover_rehearsal_runbook.md"
MATRIX_PATH = ROOT / "docs" / "ops" / "e2_3_cutover_rollback_decision_matrix.md"
EVIDENCE_TEMPLATE_PATH = ROOT / "docs" / "ops" / "e2_3_validation_evidence_template.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_e2_3_section(text: str) -> str:
    match = re.search(
        r"#### 대형 태스크 E2-3: 재적재/컷오버 리허설(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "E2-3 section not found in roadmap"
    return match.group("section")


def test_e2_3_docs_exist() -> None:
    assert RUNBOOK_PATH.exists(), f"Missing runbook: {RUNBOOK_PATH}"
    assert MATRIX_PATH.exists(), f"Missing decision matrix: {MATRIX_PATH}"
    assert EVIDENCE_TEMPLATE_PATH.exists(), (
        f"Missing evidence template: {EVIDENCE_TEMPLATE_PATH}"
    )


def test_e2_3_runbook_contains_required_contract_tokens() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "alembic upgrade head",
        "backfill",
        "consumer sync",
        "T_cutover",
        "UTC",
        "GET /admin/tx/{tx_id}",
        "200",
        "404",
        "duplicate",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_e2_3_decision_matrix_contains_required_tokens() -> None:
    matrix = _read(MATRIX_PATH)
    required_tokens = (
        "GO",
        "NO_GO",
        "MIGRATION_FAILED",
        "BACKFILL_FAILED",
        "SYNC_FAILED",
        "SMOKE_FAILED",
        "IDEMPOTENCY_FAILED",
    )
    for token in required_tokens:
        assert token in matrix, f"decision matrix missing token: {token}"


def test_e2_3_evidence_template_contains_required_tokens() -> None:
    template = _read(EVIDENCE_TEMPLATE_PATH)
    required_tokens = (
        "command",
        "exit_code",
        "UTC timestamp",
        "owner",
        "result",
    )
    for token in required_tokens:
        assert token in template, f"evidence template missing token: {token}"


def test_roadmap_e2_3_section_references_artifacts_and_evidence_policy() -> None:
    e2_3_section = _extract_e2_3_section(_read(ROADMAP_PATH))
    required_tokens = (
        "docs/ops/e2_3_reload_cutover_rehearsal_runbook.md",
        "docs/ops/e2_3_cutover_rollback_decision_matrix.md",
        "docs/ops/e2_3_validation_evidence_template.md",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in e2_3_section, f"roadmap E2-3 missing token: {token}"


def test_decisions_doc_contains_dec_245_and_dec_246() -> None:
    decisions = _read(DECISIONS_PATH)
    required_tokens = (
        "### DEC-245",
        "### DEC-246",
        "T_cutover",
        "UTC",
        "GO",
        "NO_GO",
    )
    for token in required_tokens:
        assert token in decisions, f"decision doc missing token: {token}"


def test_infra_inventory_references_e2_3_artifacts() -> None:
    inventory = _read(INFRA_INVENTORY_PATH)
    required_tokens = (
        "e2_3_reload_cutover_rehearsal_runbook.md",
        "e2_3_cutover_rollback_decision_matrix.md",
        "e2_3_validation_evidence_template.md",
    )
    for token in required_tokens:
        assert token in inventory, f"infra inventory missing token: {token}"
