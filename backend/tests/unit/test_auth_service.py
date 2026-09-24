"""
Unit tests for AuthService -- direct service calls against the DB session
fixture, no HTTP layer involved.
"""
import pytest

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.modules.auth.service import AuthService


def test_signup_creates_tenant_and_owner(db_session):
    service = AuthService(db_session)
    user, access, refresh = service.signup_tenant(
        "Acme Corp", "owner@acme.example.com", "correct-horse-battery-staple", "Ada Owner"
    )

    assert user.role.value == "owner"
    assert user.tenant_id is not None
    assert access and refresh


def test_signup_rejects_duplicate_email(db_session):
    service = AuthService(db_session)
    service.signup_tenant("Acme Corp", "owner@acme.example.com", "correct-horse-battery-staple", None)

    with pytest.raises(EmailAlreadyRegisteredError):
        service.signup_tenant("Other Co", "owner@acme.example.com", "another-password", None)


def test_login_rejects_wrong_password(db_session):
    service = AuthService(db_session)
    service.signup_tenant("Acme Corp", "owner@acme.example.com", "correct-horse-battery-staple", None)

    with pytest.raises(InvalidCredentialsError):
        service.login("owner@acme.example.com", "wrong-password")


def test_login_rejects_unknown_email(db_session):
    service = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        service.login("nobody@nowhere.example.com", "whatever")


def test_refresh_issues_new_tokens(db_session):
    service = AuthService(db_session)
    _, _, refresh_token = service.signup_tenant(
        "Acme Corp", "owner@acme.example.com", "correct-horse-battery-staple", None
    )

    new_access, new_refresh = service.refresh(refresh_token)
    assert new_access and new_refresh


def test_refresh_rejects_access_token_used_as_refresh_token(db_session):
    service = AuthService(db_session)
    _, access_token, _ = service.signup_tenant(
        "Acme Corp", "owner@acme.example.com", "correct-horse-battery-staple", None
    )

    with pytest.raises(InvalidCredentialsError):
        service.refresh(access_token)
