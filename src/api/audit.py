from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import Request


@dataclass(frozen=True)
class ActorContext:
    actor_id: str | None
    actor_roles: str | None


def extract_actor(request: Request) -> ActorContext:
    actor_id = request.headers.get("X-Actor-Id")
    actor_roles = request.headers.get("X-Actor-Roles")
    return ActorContext(actor_id=actor_id, actor_roles=actor_roles)


def build_audit_fields(
    *,
    actor: ActorContext,
    action: str,
    resource_type: str,
    resource_id: str | None,
    result: str,
    status_code: int,
    request: Request,
    duration_ms: int | None,
) -> dict[str, Any]:
    client = request.client
    query = request.url.query

    return {
        "actor_id": actor.actor_id,
        "actor_roles": actor.actor_roles,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "result": result,
        "status_code": status_code,
        "ip": client.host if client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_method": request.method,
        "request_path": request.url.path,
        "request_query": query if query else None,
        "requested_at": datetime.now(timezone.utc),
        "duration_ms": duration_ms,
    }
