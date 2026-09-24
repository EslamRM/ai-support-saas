"""
Unit tests for the require_role dependency's authorization logic, in
isolation from FastAPI's request cycle.
"""
import pytest
from fastapi import HTTPException

from app.core.dependencies import require_role
from app.modules.auth.models import UserRole


class _FakeUser:
    """Minimal stand-in with just the attribute require_role's inner
    check reads -- no need to spin up a real DB-backed User."""

    def __init__(self, role: UserRole):
        self.role = role


def test_agent_is_rejected_by_admin_gate():
    checker = require_role(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        checker(_FakeUser(UserRole.AGENT))
    assert exc_info.value.status_code == 403


def test_admin_passes_admin_gate():
    checker = require_role(UserRole.ADMIN)
    result = checker(_FakeUser(UserRole.ADMIN))
    assert result.role == UserRole.ADMIN


def test_owner_passes_admin_gate():
    """Higher-ranked roles satisfy a lower-ranked requirement."""
    checker = require_role(UserRole.ADMIN)
    result = checker(_FakeUser(UserRole.OWNER))
    assert result.role == UserRole.OWNER


def test_agent_passes_agent_gate():
    checker = require_role(UserRole.AGENT)
    result = checker(_FakeUser(UserRole.AGENT))
    assert result.role == UserRole.AGENT
