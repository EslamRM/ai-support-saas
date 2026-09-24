# API Surface

FastAPI exposes OpenAPI automatically at `/docs` and `/openapi.json`.

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`

## Tenants / knowledge base

- tenant information endpoints
- knowledge-base create/list/get endpoints

## Documents

- `POST /documents`
- `GET /documents`
- `GET /documents/{document_id}`

Upload is asynchronous and returns document status.

## Conversations

- start/list/get conversations
- send a message to a conversation

A conversation message executes the LangGraph workflow synchronously because the user
expects an interactive answer.

## Tickets

- create
- list
- get
- admin status update

## Analytics

`GET /analytics` returns:
- conversation count
- message count
- ticket count
- tickets by status
- handoff rate
- average confidence

## Health

`GET /health` is intentionally cheap and does not require authentication.

## Error contract

Domain failures return JSON:

```json
{"detail": "human-readable reason"}
```

The application maps known domain errors to 4xx status codes centrally.
