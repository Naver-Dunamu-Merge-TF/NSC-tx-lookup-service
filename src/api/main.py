from __future__ import annotations

import time

from fastapi import Depends, FastAPI, HTTPException, Request

from src.api.audit import build_audit_fields, extract_actor
from src.api.auth import require_admin_read
from src.api.constants import ADMIN_TX_LOOKUP
from src.api.schemas import AdminTxResponse
from src.api.service import build_admin_tx_response
from src.db.audit import record_admin_audit
from src.db.admin_tx import fetch_admin_tx_context
from src.db.session import session_scope

app = FastAPI(title="Backoffice Admin API")


@app.get("/admin/tx/{tx_id}", response_model=AdminTxResponse)
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
