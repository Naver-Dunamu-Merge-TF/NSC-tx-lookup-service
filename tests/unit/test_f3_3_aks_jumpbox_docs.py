from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = ROOT / "docs" / "ops" / "f3_3_aks_jumpbox_runbook.md"
TEARDOWN_PATH = ROOT / "docs" / "ops" / "f3_3_aks_jumpbox_teardown_runbook.md"
QUALITY_GATE_RUNBOOK_PATH = ROOT / "docs" / "ops" / "f3_3_quality_gate_runbook.md"
ROADMAP_PATH = ROOT / ".roadmap" / "implementation_roadmap.md"
DECISIONS_PATH = ROOT / ".specs" / "decision_open_items.md"
INFRA_INVENTORY_PATH = ROOT / ".specs" / "infra" / "tx_lookup_azure_resource_inventory.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_jumpbox_docs_exist() -> None:
    assert RUNBOOK_PATH.exists(), f"Missing runbook: {RUNBOOK_PATH}"
    assert TEARDOWN_PATH.exists(), f"Missing teardown runbook: {TEARDOWN_PATH}"


def test_runbook_contains_network_and_access_guardrails() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "nsc-vnet-dev",
        "nsc-snet-admin",
        "Bastion",
        "--public-ip-address ''",
        "az vm create",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_teardown_runbook_contains_vm_delete_and_evidence_path() -> None:
    teardown = _read(TEARDOWN_PATH)
    required_tokens = (
        "az vm delete",
        "az vm delete --resource-group 2dt-final-team4 --name jump-aks-20260224-2dt026 --yes",
        "az network nic delete",
        "az disk delete --yes",
        "az resource list --tag purpose=f3-3-jumpbox",
        "explicit requester instruction",
        "teardown_pending=true",
        "teardown_evidence_summary",
        "result=pass|blocked",
        "residual_count=0",
        ".agents/logs/verification/",
    )
    for token in required_tokens:
        assert token in teardown, f"teardown runbook missing token: {token}"


def test_runbook_contains_secure_provisioning_and_access_details() -> None:
    runbook = _read(RUNBOOK_PATH)
    required_tokens = (
        "owner=2dt026",
        "purpose=f3-3-jumpbox",
        "ttl=2026-02-24",
        "jump-aks-20260224-2dt026",
        "nic-jump-aks-20260224-2dt026",
        "osdisk-jump-aks-20260224-2dt026",
        "datadisk-jump-aks-20260224-2dt026-01",
        "--subnet nsc-snet-admin",
        "Bastion",
        "az extension show -n ssh || az extension add -n ssh",
        "kubelogin convert-kubeconfig -l azurecli",
        "kubectl cluster-info",
        "kubectl get ns txlookup",
    )
    for token in required_tokens:
        assert token in runbook, f"runbook missing token: {token}"


def test_quality_gate_runbook_references_jumpbox_required_path_and_teardown_rule() -> None:
    runbook = _read(QUALITY_GATE_RUNBOOK_PATH)
    required_tokens = (
        "docs/ops/f3_3_aks_jumpbox_runbook.md",
        "docs/ops/f3_3_aks_jumpbox_teardown_runbook.md",
        "same-day cleanup",
        "private-cluster",
    )
    for token in required_tokens:
        assert token in runbook, f"quality gate runbook missing token: {token}"


def test_roadmap_references_jumpbox_runbooks_and_recurring_validation() -> None:
    roadmap = _read(ROADMAP_PATH)
    required_tokens = (
        "docs/ops/f3_3_aks_jumpbox_runbook.md",
        "docs/ops/f3_3_aks_jumpbox_teardown_runbook.md",
        "정기 회귀",
    )
    for token in required_tokens:
        assert token in roadmap, f"roadmap missing token: {token}"


def test_decisions_doc_contains_jumpbox_policy_decision() -> None:
    decisions = _read(DECISIONS_PATH)
    required_tokens = (
        "### DEC-236",
        "same-day",
        "blocked",
        "teardown",
        "jumpbox",
    )
    for token in required_tokens:
        assert token in decisions, f"decisions missing token: {token}"


def test_infra_inventory_references_jumpbox_policy_and_latest_pilot_evidence() -> None:
    infra = _read(INFRA_INVENTORY_PATH)
    required_tokens = (
        "f3_3_aks_jumpbox_runbook.md",
        "f3_3_aks_jumpbox_teardown_runbook.md",
        "20260224_012413_f3_3_jumpbox_pilot",
        "same-day",
    )
    for token in required_tokens:
        assert token in infra, f"infra inventory missing token: {token}"
