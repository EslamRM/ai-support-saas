"""
Shared pytest fixtures.

Uses an in-memory SQLite DB, not Postgres. This works because every
model uses SQLAlchemy's generic cross-dialect types (db/base.py uses
Mapped[uuid.UUID], not the Postgres-specific UUID type) -- a deliberate
trade-off: fast, dependency-free unit/integration tests vs. testing
against the exact production engine. Anything genuinely Postgres-specific
added later (e.g. full-text search, JSONB operators) would need a
dedicated Postgres-backed test rather than relying on this fixture.

Also sets CELERY_TASK_ALWAYS_EAGER before any application module is
imported (env vars must be set before core.config.Settings() is
instantiated, since it's a module-level singleton) -- this makes
`.delay()` calls run synchronously in-process, so the document ingestion
pipeline is exercised for real in tests without a running Redis/worker.
"""
import os

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.ai.vector_store import VectorStore
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.auth.models import User, UserRole
from app.modules.conversations.models import Conversation, Message  # noqa: F401 -- registers tables
from app.modules.documents.models import Document, DocumentChunk  # noqa: F401 -- registers tables
from app.modules.knowledge_base.models import KnowledgeBase  # noqa: F401 -- registers tables
from app.modules.tenants.models import Tenant
from app.modules.tickets.models import Ticket  # noqa: F401 -- registers tables

# StaticPool is required here: SQLAlchemy's default pool hands each thread
# its own physical connection, and each fresh connection to
# "sqlite:///:memory:" is a DISTINCT, empty in-memory database. Starlette's
# TestClient runs the app in a worker thread, so without StaticPool the
# fixture's setup connection and the request's connection would silently
# be two different databases -- tables created in one are invisible to
# the other. StaticPool forces every checkout to reuse the same single
# connection, which is also why check_same_thread=False is needed.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # workers/document_tasks.py deliberately does NOT use FastAPI's
    # get_db dependency (workers aren't request-scoped -- see its
    # docstring), so overriding get_db alone doesn't redirect it. Without
    # this, the Celery task (run synchronously via eager mode) would try
    # to open a real connection to the production Postgres URL in
    # settings.database_url and fail outside a full docker-compose
    # environment. Point it at the same in-memory engine/session the rest
    # of the test uses instead.
    import app.workers.document_tasks as document_tasks_module

    monkeypatch.setattr(document_tasks_module, "SessionLocal", TestingSessionLocal)

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_tenant_and_owner(db_session, *, tenant_name: str, email: str) -> tuple[Tenant, User]:
    tenant = Tenant(name=tenant_name, slug=tenant_name.lower().replace(" ", "-"))
    db_session.add(tenant)
    db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password("correct-horse-battery-staple"),
        role=UserRole.OWNER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)
    return tenant, user


@pytest.fixture()
def tenant_a(db_session) -> tuple[Tenant, User]:
    """First of a PAIR of tenants -- most tenant-isolation tests need two
    tenants to prove one can't see the other's data."""
    return _make_tenant_and_owner(db_session, tenant_name="Acme Corp", email="owner@acme.example.com")


@pytest.fixture()
def tenant_b(db_session) -> tuple[Tenant, User]:
    return _make_tenant_and_owner(db_session, tenant_name="Globex Inc", email="owner@globex.example.com")


def auth_headers_for(user: User) -> dict:
    token = create_access_token(str(user.id), str(user.tenant_id), user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def vector_store() -> VectorStore:
    """Embedded, fully offline Qdrant -- no server, no network. Function-
    scoped so each test gets a clean collection with no cross-test
    pollution."""
    return VectorStore(client=QdrantClient(":memory:"), vector_size=1536)


@pytest.fixture()
def patch_vector_store(monkeypatch, vector_store: VectorStore) -> VectorStore:
    """Redirects app.workers.document_tasks's VectorStore() calls to the
    shared embedded instance above, instead of the real Qdrant server at
    settings.qdrant_url. Request this fixture (in addition to `client`)
    in any test that exercises document upload through the HTTP API, so
    the full extract->chunk->embed->index pipeline runs for real without
    a running Qdrant container."""
    import app.workers.document_tasks as document_tasks_module

    monkeypatch.setattr(document_tasks_module, "VectorStore", lambda *a, **k: vector_store)
    return vector_store


@pytest.fixture()
def patch_agent_graph(monkeypatch, vector_store: VectorStore):
    """Redirects ConversationService.send_message's default
    build_agent_graph() call to one wired to the same embedded Qdrant
    instance and the offline FakeChatModel, so POST
    /conversations/{id}/messages runs the REAL agent graph end-to-end in
    tests -- no live Qdrant, no OpenAI API key needed. See
    conversations/service.py's docstring on why this monkeypatch target
    (not a bound default parameter) is what makes injection possible."""
    import app.modules.conversations.service as conversations_service_module
    from app.modules.agent.graph import build_agent_graph
    from app.modules.agent.llm import FakeChatModel

    def _fake_graph_factory():
        return build_agent_graph(vector_store=vector_store, chat_model=FakeChatModel())

    monkeypatch.setattr(conversations_service_module, "build_agent_graph", _fake_graph_factory)
    return vector_store
