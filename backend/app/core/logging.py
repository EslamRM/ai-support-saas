"""
Structured observability for the modular monolith.

Design:
- JSON logs are emitted through structlog.
- Request/tenant/user/conversation identifiers are contextvars, so every
  event can be correlated without passing logger objects through business code.
- Request IDs are returned as X-Request-ID for client-side correlation.
- Payloads are deliberately metadata-only: no passwords, JWTs, API keys,
  document contents, or customer messages are logged.
"""
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.tenancy import clear_current_tenant, get_current_tenant_for_logging

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_conversation_id: ContextVar[str | None] = ContextVar("conversation_id", default=None)


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_conversation_id(value: str | None) -> None:
    _conversation_id.set(value)


def clear_observability_context() -> None:
    _request_id.set(None)
    _conversation_id.set(None)
    clear_current_tenant()


def _add_context(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["request_id"] = get_request_id()
    tenant = get_current_tenant_for_logging()
    if tenant:
        event_dict["tenant_id"] = str(tenant.tenant_id)
        event_dict["user_id"] = str(tenant.user_id)
        event_dict["user_role"] = tenant.role
    conversation_id = _conversation_id.get()
    if conversation_id:
        event_dict["conversation_id"] = conversation_id
    return event_dict


def configure_logging() -> None:
    """Configure once at process startup; safe to call more than once."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_context,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def new_request_id() -> str:
    return str(uuid.uuid4())
