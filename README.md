# AI Customer Support Agent SaaS

Multi-tenant SaaS platform where companies build an AI support agent grounded in their own
knowledge base (RAG + LangGraph), with human handoff via ticketing when the agent can't help.

Built as a portfolio project demonstrating Senior/Staff-level AI engineering decisions, not
just a working demo. See `docs/` for the full design rationale.

## Status

This repository is being built incrementally, phase by phase (see `docs/architecture.md` for
the roadmap). Current phase: **Phase 15 — Cost Control, complete.** The React frontend
(`frontend/`) now gives every backend phase a UI: login/signup, knowledge base management with
document upload, conversation transcripts you can send test messages into, tickets with
role-gated status updates, and a real analytics overview. Backend: `cd backend && pytest -q` →
74 passed. Frontend: `cd frontend && npm run build` → builds clean (TypeScript strict mode, no
errors). See `docs/tickets.md`, `docs/memory.md`, `docs/agent.md`, `docs/rag.md` for the deep
explanations of each phase, and `docs/troubleshooting.md` for real bugs hit along the way.

## Running it locally

1. Copy `.env.example` to `.env`.
2. Set a strong `JWT_SECRET_KEY`. Add `OPENAI_API_KEY` if you want real model responses.
3. Start the full stack:

```bash
docker compose up --build
```

Open `http://localhost:5173` for the dashboard and `http://localhost:8000/docs` for API
documentation.

For zero-cost automated tests, no external API key or running infrastructure is required
once the backend dependencies are installed:

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Without an OpenAI key the application uses deterministic fake providers. Those providers
prove plumbing and routing, not semantic AI quality; use `tests/evaluation/dataset.jsonl`
with a real provider for RAG/answer-quality evaluation.

## Repository Structure

```
backend/
  app/
    core/           # config, security, tenancy context, shared FastAPI dependencies
    db/              # SQLAlchemy base + session management
    modules/         # one folder per bounded context (tenants, auth, knowledge_base,
                      # documents, conversations, agent, tickets, analytics)
    workers/         # Celery app + background tasks (document processing pipeline)
  alembic/           # database migrations
  tests/
    unit/            # service-layer logic, no DB/network
    integration/     # API + DB integration tests
    security/        # tenant isolation / IDOR / RBAC proof tests
frontend/            # React + TypeScript + Tailwind admin dashboard (staff-facing)
  src/
    api/              # centralized fetch client + TypeScript types
    auth/              # login/logout/session context
    components/         # shared layout + UI primitives
    pages/                # one file per route
docs/                # architecture, security, RAG, agent, memory, tickets, ADRs, interview prep
docker-compose.yml     # local full-stack environment
scripts/             # dev/setup scripts
```

## Why this structure

Each module under `app/modules/` follows the same internal shape
(`router.py` / `schemas.py` / `service.py` / `models.py` / `repository.py`) except
`agent/`, which is graph-shaped (`state.py` / `graph.py` / `nodes/` / `tools.py` / `llm.py`)
because its job is orchestrating a decision process, not persisting a CRUD resource.
See `docs/architecture.md` and `docs/adr/ADR-001-modular-monolith.md` for the reasoning.

## Engineering review

The project is intentionally a modular monolith. Phase 9 adds structured observability,
Phase 10 adds bounded retries and transaction hardening, Phase 11 adds AI security controls,
Phase 12 adds an evaluation dataset, Phase 13 expands tests, Phase 14 makes the full stack
runnable with Docker Compose, and Phase 15 documents provider/cost controls.

See:
- `docs/observability.md`
- `docs/reliability.md`
- `docs/ai-security.md`
- `docs/evaluation.md`
- `docs/scaling.md`
- `docs/interview-questions.md`
- `docs/final-engineering-review.md`

