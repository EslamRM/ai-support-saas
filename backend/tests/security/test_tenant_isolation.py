"""
Proves the tenant-isolation guarantee from get_current_user: a JWT cannot
be used to act as another tenant, even if its tenant_id claim is forged,
because the dependency re-derives tenant_id from the user's actual DB row.
"""
from app.core.security import create_access_token
from tests.conftest import auth_headers_for


def test_forged_tenant_claim_in_token_is_rejected(client, tenant_a, tenant_b):
    _, user_a = tenant_a
    _, tenant_b_record_owner = tenant_b

    # Forge a token: user_a's real id, but claiming tenant_b's tenant_id
    # instead of user_a's actual tenant_id.
    forged_token = create_access_token(str(user_a.id), str(tenant_b_record_owner.tenant_id), user_a.role.value)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged_token}"})

    # Must be rejected: get_current_user compares the token's tenant_id
    # claim against user_a's real tenant_id column and finds a mismatch.
    assert response.status_code == 401


def test_legit_token_returns_only_own_profile(client, tenant_a):
    tenant, user = tenant_a
    response = client.get("/auth/me", headers=auth_headers_for(user))

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == str(tenant.id)
    assert body["email"] == user.email


def test_tenants_me_returns_only_the_callers_tenant(client, tenant_a, tenant_b):
    tenant, user = tenant_a
    other_tenant, _ = tenant_b

    response = client.get("/tenants/me", headers=auth_headers_for(user))

    assert response.status_code == 200
    assert response.json()["id"] == str(tenant.id)
    assert response.json()["id"] != str(other_tenant.id)


def test_deactivated_user_is_rejected_even_with_valid_token(client, tenant_a, db_session):
    _, user = tenant_a
    token = create_access_token(str(user.id), str(user.tenant_id), user.role.value)

    user.is_active = False
    db_session.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
