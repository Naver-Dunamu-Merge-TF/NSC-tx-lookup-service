from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"
CONFIG_README_PATH = ROOT / "configs" / "README.md"
INFRA_INVENTORY_PATH = ROOT / ".specs" / "infra" / "tx_lookup_azure_resource_inventory.md"

SECRET_RUNBOOK_PATH = ROOT / "docs" / "ops" / "e2_2_secret_identity_transition_runbook.md"
RBAC_MATRIX_PATH = ROOT / "docs" / "ops" / "e2_2_rbac_matrix.md"
AUTH_OBS_RUNBOOK_PATH = ROOT / "docs" / "ops" / "e2_2_auth_failure_observability_runbook.md"
EVIDENCE_TEMPLATE_PATH = ROOT / "docs" / "ops" / "e2_2_validation_evidence_template.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_e2_2_section(text: str) -> str:
    match = re.search(
        r"#### 대형 태스크 E2-2: 시크릿/권한 전환(?P<section>.*?)(?=\n#### |\n### |\Z)",
        text,
        re.S,
    )
    assert match, "E2-2 section not found in roadmap"
    return match.group("section")


def test_e2_2_docs_exist() -> None:
    assert SECRET_RUNBOOK_PATH.exists(), f"Missing runbook: {SECRET_RUNBOOK_PATH}"
    assert RBAC_MATRIX_PATH.exists(), f"Missing matrix: {RBAC_MATRIX_PATH}"
    assert AUTH_OBS_RUNBOOK_PATH.exists(), (
        f"Missing runbook: {AUTH_OBS_RUNBOOK_PATH}"
    )
    assert EVIDENCE_TEMPLATE_PATH.exists(), (
        f"Missing template: {EVIDENCE_TEMPLATE_PATH}"
    )


def test_secret_transition_runbook_contains_required_contract_tokens() -> None:
    runbook = _read(SECRET_RUNBOOK_PATH)
    required_tokens = (
        "SAS/env",
        "Key Vault + Managed Identity",
        "txlookup-database-url",
        "txlookup-kafka-sasl-password",
        "txlookup-appinsights-connection-string",
        "local",
        "dev",
        "prod",
        "rollback",
        "owner",
        "ttl",
    )
    for token in required_tokens:
        assert token in runbook, f"secret transition runbook missing token: {token}"


def test_rbac_matrix_contains_least_privilege_and_eventhubs_external_ownership() -> None:
    matrix = _read(RBAC_MATRIX_PATH)
    required_tokens = (
        "least privilege",
        "Principal",
        "Role",
        "Scope",
        "Owner",
        "Approval",
        "Evidence command",
        "Event Hubs",
        "external ownership",
        "DB",
        "AKS",
        "Key Vault",
    )
    for token in required_tokens:
        assert token in matrix, f"rbac matrix missing token: {token}"


def test_auth_observability_runbook_contains_401_403_and_audit_split() -> None:
    runbook = _read(AUTH_OBS_RUNBOOK_PATH)
    required_tokens = (
        "401",
        "403",
        "admin_audit_logs",
        "AppInsights",
        "Gateway",
        "status_code in (200,404)",
        "result_count",
    )
    for token in required_tokens:
        assert token in runbook, f"auth observability runbook missing token: {token}"


def test_evidence_template_contains_required_fields_and_path_policy() -> None:
    template = _read(EVIDENCE_TEMPLATE_PATH)
    required_tokens = (
        "`command`",
        "`exit_code`",
        "UTC timestamp",
        "`owner`",
        "`result`",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in template, f"evidence template missing token: {token}"


def test_configs_readme_contains_local_env_and_dev_prod_keyvault_policy() -> None:
    config_readme = _read(CONFIG_README_PATH)
    required_tokens = (
        "local",
        "dev`/`prod",
        "Key Vault",
        "source of truth",
    )
    for token in required_tokens:
        assert token in config_readme, f"configs README missing token: {token}"


def test_roadmap_e2_2_section_marked_complete_with_artifact_links() -> None:
    e2_2_section = _extract_e2_2_section(_read(ROADMAP_PATH))
    required_tokens = (
        "- [x] SAS/env 기반 전달에서 Key Vault + Managed Identity 방식으로 전환 설계",
        "- [x] 최소권한 RBAC 매트릭스(DB/Event Hubs/AKS/Key Vault) 확정",
        "- [x] 접근 실패(401/403/권한오류) 관측 경로와 감사 경로 분리 정의",
        "docs/ops/e2_2_secret_identity_transition_runbook.md",
        "docs/ops/e2_2_rbac_matrix.md",
        "docs/ops/e2_2_auth_failure_observability_runbook.md",
        "docs/ops/e2_2_validation_evidence_template.md",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in e2_2_section, f"roadmap E2-2 missing token: {token}"


def test_decisions_doc_contains_dec_242_244_with_required_policies() -> None:
    decisions = _read(DECISIONS_PATH)
    required_tokens = (
        "### DEC-242",
        "### DEC-243",
        "### DEC-244",
        "Event Hubs",
        "external ownership",
        "Key Vault + Managed Identity",
        "401/403",
        "admin_audit_logs",
    )
    for token in required_tokens:
        assert token in decisions, f"decisions doc missing token: {token}"


def test_infra_inventory_references_e2_2_artifacts() -> None:
    inventory = _read(INFRA_INVENTORY_PATH)
    required_tokens = (
        "e2_2_secret_identity_transition_runbook.md",
        "e2_2_rbac_matrix.md",
        "e2_2_auth_failure_observability_runbook.md",
    )
    for token in required_tokens:
        assert token in inventory, f"infra inventory missing token: {token}"
