from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.schemas import AdminTxResponse
from src.api.service import build_admin_tx_response
from src.db.admin_tx import fetch_admin_tx_context
from src.db.session import session_scope

app = FastAPI(title="Backoffice Admin API")


@app.get("/admin/tx/{tx_id}", response_model=AdminTxResponse)
def get_admin_tx(tx_id: str) -> AdminTxResponse:
    with session_scope() as session:
        context = fetch_admin_tx_context(session, tx_id)
        if context is None:
            raise HTTPException(status_code=404, detail="tx_id not found")

        return build_admin_tx_response(context)
