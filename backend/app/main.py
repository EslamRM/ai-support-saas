"""
FastAPI application entrypoint.

Responsibility: wire up the app instance only -- middleware registration,
router mounting, exception handlers, startup/shutdown hooks. No business
logic lives here. Each module owns its own router; this file assembles
them.
"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging import configure_logging, clear_observability_context, new_request_id, set_request_id
import structlog


from app.core.exceptions import (
    AIOutputError,
    AIProviderUnavailableError,
    DomainError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TenantMismatchError,
)
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.conversations.router import router as conversations_router
from app.modules.conversations.service import ConversationNotFoundError
from app.modules.documents.extraction import ExtractionFailedError, UnsupportedContentTypeError
from app.modules.documents.router import router as documents_router
from app.modules.documents.service import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.modules.knowledge_base.router import router as knowledge_base_router
from app.modules.knowledge_base.service import KnowledgeBaseNotFoundError
from app.modules.tenants.router import router as tenants_router
from app.modules.tickets.router import router as tickets_router
from app.modules.tickets.service import TicketNotFoundError

configure_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(title="AI Customer Support Agent SaaS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    set_request_id(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        rate_limited_path = (
            request.url.path.startswith("/auth/")
            or request.url.path == "/documents"
            or (request.url.path.startswith("/conversations/") and request.method == "POST")
        )
        if rate_limited_path:
            client_host = request.client.host if request.client else "unknown"
            if not limiter.allow(client_host):
                logger.warning("http.request.rate_limited", path=request.url.path)
                from fastapi.responses import JSONResponse as _JSONResponse
                return _JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60", "X-Request-ID": request_id},
                )
        logger.info("http.request.started", method=request.method, path=request.url.path)
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception("http.request.failed", method=request.method, path=request.url.path)
        raise
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "http.request.completed",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        # The context is request-local. Do not leak IDs to the next request.
        clear_observability_context()



# One exception handler for the whole DomainError hierarchy, with a status
# map per concrete type. New domain exceptions get a one-line entry here
# instead of a new try/except somewhere in a route handler.
_STATUS_MAP: dict[type[DomainError], int] = {
    EmailAlreadyRegisteredError: 409,
    InvalidCredentialsError: 401,
    TenantMismatchError: 403,
    KnowledgeBaseNotFoundError: 404,
    DocumentNotFoundError: 404,
    ConversationNotFoundError: 404,
    TicketNotFoundError: 404,
    UnsupportedFileTypeError: 415,
    FileTooLargeError: 413,
    UnsupportedContentTypeError: 415,
    ExtractionFailedError: 422,
    AIProviderUnavailableError: 503,
    AIOutputError: 502,
}


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _STATUS_MAP.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc) or exc.__class__.__name__})


app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(knowledge_base_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(tickets_router)
app.include_router(analytics_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
