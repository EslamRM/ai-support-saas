# Security — Authentication, RBAC, and Tenant Isolation

This document covers what Phase 3 actually implements. Broader security review
(prompt injection, file uploads, SSRF, etc.) lands in `docs/ai-security.md` and a later
phase's `docs/security.md` expansion, once there's a RAG/agent surface to attack.

## Authentication

- **Password storage:** bcrypt via passlib (`core/security.py`). Bcrypt is deliberately
  slow (adaptive cost factor) — that's the point; it makes offline brute-force expensive.
  Plaintext passwords never touch the database or logs.
- **JWT access + refresh tokens.** Access tokens are short-lived (30 min default);
  refresh tokens longer-lived (7 days default). Both carry `sub` (user id), `tenant_id`,
  `role`, `type` (`access`/`refresh` — deliberately prevents a refresh token being used
  as an access token or vice versa), `iat`, `exp`, and a `jti` (unique token id, currently
  unused but present so a revocation/blocklist can be added later without a token-format
  migration).
- **Known limitation:** there is no refresh-token revocation list in v1. A leaked refresh
  token is valid until it expires (up to 7 days) or the account is deactivated (deactivation
  IS checked on every refresh and every access-token use, since `get_current_user` and
  `AuthService.refresh` both re-fetch the user from the DB — see below). A production
  hardening step would add a Redis-backed revoked-`jti` set, checked in both paths.

## Why the DB is re-checked on every request, not just the JWT

This is the single most important security property in this phase. `get_current_user`
(`core/dependencies.py`) does not just decode and trust the JWT. It:

1. Decodes and verifies the signature (rejects tampered/expired tokens).
2. Re-fetches the `User` row from the database by the token's `sub` (user id).
3. Checks `user.is_active` — a deactivated user is rejected immediately, even with a
   token that hasn't expired yet.
4. Compares the token's `tenant_id` claim against the **database row's own** `tenant_id`
   column, and rejects on any mismatch.

A JWT is a *claim*, not a *fact*. Without step 4, a token whose `tenant_id` claim had been
tampered with (or was simply stale after some future "move user between tenants" feature)
would be trusted blindly, and every downstream tenant-scoped query would inherit the wrong
tenant. `tests/security/test_tenant_isolation.py::test_forged_tenant_claim_in_token_is_rejected`
proves this directly: it builds a syntactically valid, correctly-signed token for a real user,
but with a `tenant_id` claim that doesn't match that user's actual tenant, and asserts it's
rejected with 401.

## RBAC

Three roles, ranked `agent < admin < owner` (`core/dependencies._ROLE_RANK`). `require_role(minimum)`
returns a FastAPI dependency that 403s unless the caller's role rank is at or above the minimum.
No endpoint in Phase 3 requires elevated roles yet (register/login/refresh/me are
role-agnostic by nature) — `require_role` is unit-tested directly
(`tests/unit/test_rbac.py`) and will gate real endpoints starting Phase 4
(e.g. only `admin`+ can upload documents to a knowledge base).

**Why a plain enum column instead of a Role/Permission table:** see the docstring in
`app/modules/auth/models.py`. Three fixed, product-defined roles don't need per-tenant-configurable
permissions. If a future requirement needs tenants to define custom roles, that's the trigger
to introduce a proper `Role`/`Permission` schema — not before.

## Tenant Isolation

**Mechanism:** every tenant-owned table inherits `TenantScopedBase` (`db/base.py`), which
adds a non-nullable, indexed `tenant_id` foreign key by construction. Every repository method
that isn't an explicit, documented exception filters by `tenant_id`.

**The one documented exception:** `UserRepository.get_by_email` is *not* tenant-filtered,
because email is globally unique across the platform in v1 (see the design-decision docstring
in `auth/models.py`) and login happens before any tenant context exists — there's nothing to
filter by yet. Every other `UserRepository` method (`get_by_id_for_tenant`) *is* tenant-scoped.
This asymmetry is called out explicitly here and in the code so it reads as a deliberate
decision during a security review, not an oversight.

**Tested attack scenarios** (`tests/security/test_tenant_isolation.py`):
- Forged `tenant_id` claim in an otherwise-valid, correctly-signed JWT → rejected (401).
- A deactivated user's still-unexpired token → rejected (401).
- `GET /tenants/me` returns only the caller's own tenant, never another tenant's, even when
  a second tenant exists in the same database.

**Not yet covered** (comes with Phase 4+, once there's tenant-owned data beyond users):
IDOR on a numeric/UUID resource id across tenants (e.g. `GET /documents/{id}`), Qdrant
retrieval filtering, and the Celery job tenant re-validation pattern discussed in Phase 1/2
(worker re-derives `tenant_id` from the DB row, never trusts the job payload's copy).

## API Security Notes

- **User enumeration:** `AuthService.login` returns the identical `InvalidCredentialsError`
  for "no such email" and "correct email, wrong password." Distinguishing them would let an
  attacker enumerate which emails have accounts.
- **Input validation:** all request bodies are Pydantic models (`auth/schemas.py`) —
  malformed JSON, wrong types, or missing fields are rejected by FastAPI/Pydantic before
  reaching the service layer.
- **Secrets:** `JWT_SECRET_KEY` and (later) `OPENAI_API_KEY` are read from environment
  variables via `core/config.py` only — never hardcoded, never logged. `.env` is gitignored;
  `.env.example` documents required variables without real values.

## Common Attack Scenarios (v1 scope)

| Attack | Defense |
|---|---|
| Stolen/leaked access token | Short 30-minute expiry limits the window |
| Tampered JWT claims (role, tenant_id) | Signature verification rejects tampering; tenant_id is also cross-checked against the DB (see above) |
| Brute-force login | Bcrypt's cost factor slows offline attacks; rate limiting on `/auth/login` is a Phase 11 addition, not yet implemented — noted as a gap |
| SQL injection | SQLAlchemy's parameterized queries throughout; no raw string-interpolated SQL anywhere in the codebase |
| Password reuse across services | Out of scope — bcrypt hashing means a DB leak doesn't expose plaintext, which is the control that matters here |

## What's deliberately deferred

- Rate limiting (Phase 11)
- Refresh token revocation / blocklist
- Account lockout after repeated failed logins
- Audit log of authentication events (ties into Phase 9 observability)

These are named here so they show up in the final security review (Phase 15/`docs/final-engineering-review.md`)
as known, intentional gaps rather than being rediscovered as surprises.
