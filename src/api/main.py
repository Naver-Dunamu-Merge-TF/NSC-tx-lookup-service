import time

from fastapi import Depends, FastAPI, HTTPException
from starlette.requests import Request

from src.api.audit import build_audit_fields, extract_actor
from src.api.auth import require_admin_read
from src.api.constants import ADMIN_TX_LOOKUP
from src.api.observability import register_observability
from src.api.schemas import AdminTxResponse
from src.common.logging import configure_logging
from src.api.service import build_admin_tx_response
from src.db.audit import record_admin_audit
from src.db.admin_tx import fetch_admin_tx_context
from src.db.session import session_scope

configure_logging()
app = FastAPI(
    title="Backoffice Admin API",
    description=(
        "관리자용 거래 조회 API. "
        "원장 엔트리 기반 tx_id 조회와 PAYMENT/RECEIVE 페어링 정보를 제공합니다."
    ),
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Admin Transaction",
            "description": "관리자 거래 조회 엔드포인트. ADMIN_READ 역할 필요.",
        },
    ],
)
register_observability(app)


@app.get(
    "/admin/tx/{tx_id}",
    response_model=AdminTxResponse,
    summary="거래 단건 조회",
    description=(
        "tx_id로 단일 원장 엔트리를 조회합니다. "
        "PAYMENT/RECEIVE 페어링이 완료된 경우 반대편 엔트리 정보도 포함됩니다. "
        "조회 시 감사 로그가 자동 기록됩니다."
    ),
    tags=["Admin Transaction"],
    responses={
        401: {"description": "인증 실패 — JWT 토큰 누락 또는 만료"},
        403: {"description": "권한 부족 — ADMIN_READ 역할 필요"},
        404: {"description": "해당 tx_id의 거래를 찾을 수 없음"},
    },
)
def get_admin_tx(
    tx_id: str,
    request: Request,
    _actor=Depends(require_admin_read),
) -> AdminTxResponse:
    start = time.monotonic()
    actor = extract_actor(request)
    result = "FOUND"
    status_code = 200
    response: AdminTxResponse | None = None

    with session_scope() as session:
        context = fetch_admin_tx_context(session, tx_id)
        if context is None:
            result = "NOT_FOUND"
            status_code = 404
        else:
            response = build_admin_tx_response(context)

        duration_ms = int((time.monotonic() - start) * 1000)
        audit_fields = build_audit_fields(
            actor=actor,
            action=ADMIN_TX_LOOKUP,
            resource_type="TX",
            resource_id=tx_id,
            result=result,
            status_code=status_code,
            request=request,
            duration_ms=duration_ms,
        )
        record_admin_audit(session, audit_fields)

    if response is None:
        raise HTTPException(status_code=404, detail="tx_id not found")

    return response
