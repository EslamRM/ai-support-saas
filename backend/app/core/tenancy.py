"""
Responsibility: the single source of truth for "what is the current tenant"
during a request -- for OBSERVABILITY purposes only.

IMPORTANT: this contextvar is NOT used for authorization decisions. Every
authorization check (RBAC, tenant-scoped queries) uses the TenantContext
that core/dependencies.get_current_user explicitly returns via FastAPI's
Depends() and passes down through service/repository calls as a normal
function argument. Contextvars are convenient but implicit and can behave
surprisingly across async boundaries (e.g. a Celery task or background
task that outlives the request) -- implicit state is the wrong tool for
"can this caller see this tenant's data". It's set here purely so
structured logging (core/logging.py) can enrich every log line with
tenant_id/user_id without threading a logger context through every call.
"""
from contextvars import ContextVar
from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class TenantContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str


_current_tenant: ContextVar["TenantContext | None"] = ContextVar("current_tenant", default=None)


def set_current_tenant(ctx: TenantContext) -> None:
    _current_tenant.set(ctx)


def get_current_tenant_for_logging() -> "TenantContext | None":
    """Returns None outside a request (e.g. at import time, in a script).
    Callers doing anything security-sensitive must NOT use this -- use the
    explicit CurrentUser dependency instead."""
    return _current_tenant.get()


def clear_current_tenant() -> None:
    """Clear request-local tenant enrichment after an HTTP request."""
    _current_tenant.set(None)
