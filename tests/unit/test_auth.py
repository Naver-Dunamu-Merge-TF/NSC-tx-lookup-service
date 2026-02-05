from __future__ import annotations

from src.api.auth import extract_actor_id, extract_roles, mask_query


def test_extract_roles_combines_sources() -> None:
    claims = {
        "roles": ["ADMIN_READ"],
        "scp": "ADMIN_AUDIT OTHER",
    }
    roles = extract_roles(claims, ["roles", "scp"])
    assert "ADMIN_READ" in roles
    assert "ADMIN_AUDIT" in roles


def test_extract_actor_id_prefers_first_match() -> None:
    claims = {"sub": "user-1", "email": "user@example.com"}
    actor = extract_actor_id(claims, ["sub", "email"])
    assert actor == "user-1"


def test_mask_query_hides_sensitive_keys() -> None:
    query = "token=secret&foo=bar&access_token=top"
    masked = mask_query(query, ["token", "access_token"])
    assert masked is not None
    assert "token=%2A%2A%2A" in masked
    assert "access_token=%2A%2A%2A" in masked
    assert "foo=bar" in masked
