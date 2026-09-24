# Troubleshooting

## `OPENAI_API_KEY` is empty

This is valid for tests/offline development. Fake embeddings and a fake chat model are used.
They are not semantic-quality providers.

## Qdrant connection errors

Confirm:

```bash
docker compose ps qdrant
curl http://localhost:6333/collections
```

If Qdrant is unavailable, retrieval cannot be trusted as "empty"; restart the service and
reprocess failed documents.

## Redis / Celery jobs not running

Check:

```bash
docker compose logs worker
docker compose logs redis
```

Documents remain in PostgreSQL with a processing status. Requeue failed/pending jobs after
the worker is healthy.

## Database migration errors

Check:

```bash
docker compose logs backend
cd backend
alembic current
alembic history
```

Do not delete production migration history to fix a schema mismatch.

## Frontend cannot call backend

Verify:
- backend is on port 8000
- frontend is on 5173
- Vite proxy is enabled in development
- CORS is configured for the deployed frontend origin

## `401` from an apparently valid JWT

The API deliberately re-fetches the user from PostgreSQL. A deactivated user or a token with
a mismatched tenant claim is rejected.

## Rate limiting

The local limiter is process-local. Multiple API replicas do not share its counters.
Move this boundary to Redis or the API gateway before horizontal scaling.

## Logs

Every request returns `X-Request-ID`. Search logs by that ID first, then narrow by tenant and
conversation identifiers.

## Document stuck in `FAILED`

Read the document's `error_message` and worker logs. Common causes are invalid content,
provider timeouts, embedding failures, or Qdrant connectivity.
