# Local Deployment

## Prerequisites

- Docker Engine + Docker Compose
- Git
- Node.js 20+ only if running the frontend outside Docker

## Services

The compose file runs:
- PostgreSQL
- Redis
- Qdrant
- FastAPI backend
- Celery worker
- React/Vite frontend

## Environment

Copy `.env.example` to `.env`.

Set at minimum:

```text
JWT_SECRET_KEY=replace-with-a-long-random-secret
OPENAI_API_KEY=...
```

The OpenAI key is optional for offline development/tests; the application falls back to
deterministic fake providers.

## Start

```bash
docker compose up --build
```

Backend:
`http://localhost:8000`

Swagger:
`http://localhost:8000/docs`

Frontend:
`http://localhost:5173`

## Migrations

The backend container runs Alembic migrations before serving the API. For a production
deployment, prefer a separate migration job so only one process owns schema migration.

## Production hardening

Before exposing the service publicly:
- replace development credentials
- use a strong JWT secret
- use TLS
- configure trusted CORS origins
- move rate limiting to shared Redis/gateway
- add object storage and malware scanning
- configure centralized logs/metrics
- add database backups
- define data retention/deletion policies
- use a real secrets manager
