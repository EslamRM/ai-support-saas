"""
Responsibility: application-wide domain exception types.

Services raise these; main.py registers ONE exception handler per type
(via the DomainError base) that maps it to an HTTP status. Route handlers
never contain try/except-to-HTTPException boilerplate -- they just call
the service and let exceptions propagate.
"""


class DomainError(Exception):
    """Base class for all domain-level errors."""


class EmailAlreadyRegisteredError(DomainError):
    """Raised on signup when the email is already in use."""


class InvalidCredentialsError(DomainError):
    """Raised on login/refresh failure. Deliberately generic message at the
    HTTP boundary (never reveals whether the email exists) -- see
    docs/security.md, user enumeration."""


class TenantMismatchError(DomainError):
    """Raised when a resource's tenant_id doesn't match the caller's tenant
    context. Should be structurally rare -- repositories filter by
    tenant_id already -- this is the failsafe if one doesn't."""


class AIProviderUnavailableError(DomainError):
    """An upstream AI/vector provider remained unavailable after bounded retries."""


class AIOutputError(DomainError):
    """The provider returned a response that failed the required structured contract."""
