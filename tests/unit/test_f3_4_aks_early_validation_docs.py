from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = ROOT / "docs" / "ops" / "f3_4_aks_early_validation_runbook.md"
EVIDENCE_TEMPLATE_PATH = ROOT / "docs" / "ops" / "f3_4_validation_evidence_template.md"
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_f3_4_section(text: str) -> str:
    import re

    match = re.search(
        r"#### 대형 태스크 F3-4: AKS 조기 검증 트랙(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "F3-4 section not found in roadmap"
    return match.group("section")


def test_f3_4_docs_exist() -> None:
    assert RUNBOOK_PATH.exists(), f"Missing runbook: {RUNBOOK_PATH}"
    assert EVIDENCE_TEMPLATE_PATH.exists(), (
        f"Missing evidence template: {EVIDENCE_TEMPLATE_PATH}"
    )


def test_f3_4_docs_contain_required_baseline_tokens() -> None:
    runbook = _read(RUNBOOK_PATH)
    template = _read(EVIDENCE_TEMPLATE_PATH)
    required_tokens = (
        "provisioningState=Succeeded",
        "txlookup",
        "API/Consumer image pull",
        "DB/Event Hubs",
        "GET /admin/tx/{tx_id}",
        "200",
        "404",
        "consumer lag",
        "consumer_freshness_seconds",
        ".agents/logs/verification/",
    )
    doc_text = f"{runbook}\n{template}"
    for token in required_tokens:
        assert token in doc_text, f"missing token: {token}"


def test_runbook_contains_aks_readiness_and_namespace_commands() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "az aks show -g 2dt-final-team4 -n nsc-aks-dev --query provisioningState -o tsv",
        "kubectl get ns txlookup",
        "kubectl create ns txlookup",
        "provisioningState=Succeeded",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_runbook_contains_startup_smoke_commands_and_dependencies() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "API_DEPLOYMENT",
        "CONSUMER_DEPLOYMENT",
        "kubectl -n txlookup set image deployment/${API_DEPLOYMENT}",
        "kubectl -n txlookup set image deployment/${CONSUMER_DEPLOYMENT}",
        "kubectl -n txlookup rollout status deployment/${API_DEPLOYMENT}",
        "kubectl -n txlookup rollout status deployment/${CONSUMER_DEPLOYMENT}",
        "DB connection",
        "Event Hubs connection",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_runbook_and_template_contain_api_smoke_metrics_and_retry_contract() -> None:
    runbook = _read(RUNBOOK_PATH)
    template = _read(EVIDENCE_TEMPLATE_PATH)
    required_tokens = (
        "GET /admin/tx/{tx_id}",
        "returns 200",
        "returns 404",
        "consumer lag",
        "consumer_freshness_seconds",
        "failure_classification",
        "retry_at_utc",
        "unblock_criteria",
    )
    doc_text = f"{runbook}\n{template}"
    for token in required_tokens:
        assert token in doc_text, f"missing token: {token}"


def test_roadmap_and_decision_docs_reference_f3_4_artifacts_and_policy() -> None:
    roadmap_section = _extract_f3_4_section(_read(ROADMAP_PATH))
    decisions = _read(DECISIONS_PATH)
    roadmap_tokens = (
        "docs/ops/f3_4_aks_early_validation_runbook.md",
        "docs/ops/f3_4_validation_evidence_template.md",
    )
    decision_tokens = (
        "### DEC-237",
        "retry owner",
        "retry date",
        "provisioningState=Succeeded",
        "txlookup namespace ready",
        "API 200/404 smoke pass",
        "lag/freshness evidence pass",
    )
    for token in roadmap_tokens:
        assert token in roadmap_section, f"roadmap F3-4 missing token: {token}"
    for token in decision_tokens:
        assert token in decisions, f"decisions missing token: {token}"
