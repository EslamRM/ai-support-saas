# Ticket Generation

This document explains what `backend/app/modules/tickets/` and the ticket-creation path in
`agent/tools.py` implement, and — this phase's central design question — **why ticket
creation is a tool invoked deterministically by application code, not something baked into
the LLM prompt or left to the LLM's own discretion to call.**

## The flow

```
Customer: "I was charged twice."
  -> classify_intent: needs_retrieval = True
  -> retrieve_knowledge: searches the KB, finds nothing relevant (no billing docs indexed)
  -> generate_answer: "I don't have enough information..." (grounded=False)
  -> quality_check: retrieved_chunks empty -> route = "handoff"
  -> ConversationService.send_message sees route == "handoff":
       -> chat_model.summarize_for_ticket(question, answer, history) -> title + description
       -> create_ticket_tool(...) -> persists a Ticket row, status=open, priority=medium
  -> assistant message returned to the customer, with ticket_id in its metadata
```

Exercised end-to-end in `tests/integration/test_tickets.py::test_unanswerable_question_creates_a_ticket`.

## Why NOT "just put ticket creation in the LLM prompt"

Two different bad versions of this are worth naming explicitly, because both are tempting
shortcuts:

**Bad version 1 — ask the model to output ticket JSON as part of the same call that generates
the answer.** This conflates two different structured outputs (an `AgentAnswer` for the
customer, a ticket for support staff) into one prompt, which bloats the prompt and makes both
outputs harder to get reliably right. It also means the model is being asked to decide *both*
"should I write an answer" *and* "should a ticket exist" in the same breath — exactly the kind
of overloaded responsibility that makes prompts fragile.

**Bad version 2 — give the model `create_ticket` as an OpenAI-style function-calling tool and
let it decide, autonomously, whether to call it.** This is the more subtle mistake, and the one
actually worth defending against in an interview: **the routing decision is already made,
deterministically, by `quality_check`** (Phase 5), using `grounded`/`confidence`/
`retrieved_chunks` signals the model itself produced. If the model *also* gets to independently
decide whether to call `create_ticket`, there are now two decision-makers for one decision —
and they can disagree. The model could decline to call the tool even though `quality_check`
already determined the answer wasn't good enough (a customer with a real billing problem gets
no ticket and no real answer), or it could call the tool speculatively on a question
`quality_check` would have happily answered (needless ticket noise for support staff). This is
the exact "unnecessarily autonomous agent" anti-pattern this project avoids elsewhere
(`classify_intent` and `quality_check` are both plain deterministic functions, not LLM calls,
for the same reason — see `docs/agent.md`).

## What the LLM's role actually is here

Narrow and safe: `ChatModel.summarize_for_ticket` writes a good title/description **given that
a ticket has already been decided to exist.** It doesn't decide whether one should. This is a
genuinely good use of the model — compressing a conversation into a title a human can scan in a
queue is exactly the kind of task an LLM does well and a deterministic rule doesn't — while
keeping the higher-stakes decision (does this customer get auto-answered or handed to a human)
entirely deterministic and auditable.

## Tool design, per the "every tool must have" checklist

- **Explicit input schema** — `CreateTicketInput` (Pydantic). `tenant_id` and
  `conversation_id` are required, non-optional fields; there's no way to construct a valid
  instance without them, which makes "forgot to scope this to a tenant" a schema-validation
  failure, not a possible runtime gap.
- **Tenant validation** — delegated to `TicketService.create_ticket`, which confirms the
  `conversation_id` belongs to the calling tenant before writing anything (the same IDOR check
  pattern used for document upload and starting a conversation). Proven directly by
  `test_ticket_creation_rejects_another_tenants_conversation_id`.
- **Authorization** — the AI's own ticket-creation path never goes through HTTP/RBAC at all
  (it's invoked by trusted application code, `ConversationService`, which already knows the
  authenticated tenant from the conversation). The staff-facing manual-creation and
  status-update endpoints (`tickets/router.py`) do go through the normal `CurrentUser`/
  `require_role` checks — status updates specifically require `admin`+, since an `agent`-level
  account shouldn't be able to unilaterally close out tickets.
- **Error handling** — a failure in `summarize_for_ticket` or `create_ticket_tool` currently
  propagates as an unhandled exception out of `send_message`, same honest gap as noted in
  `docs/agent.md` for the rest of the graph — Phase 10 is where this gets designed properly.
- **Logging** — `create_ticket_tool` logs tenant/conversation/priority on every invocation
  (`agent.tool.create_ticket`), ahead of Phase 9's full observability pass.

## A known, documented consistency gap

Ticket creation (inside `create_ticket_tool`, via `TicketService`) commits in its own
transaction, separate from the assistant `Message` row's commit right after it in
`ConversationService.send_message`. A crash between the two could leave a ticket with no
message recording it, or an assistant message referencing a `ticket_id` whose ticket didn't
actually persist. Wrapping both writes in a single transaction is a real reliability
improvement — named here rather than fixed silently, because it belongs with the rest of
Phase 10's retry/transaction-boundary design, not bolted on ad hoc.

## Priority is always "medium" in v1

There's no automatic urgency classification — "I was charged twice" and "how do I change my
display name" get the same default priority. A content-based classifier (or a second, narrow
LLM call similar to `summarize_for_ticket`) is a real improvement, deferred because it's another
judgment surface without evidence yet that simplistic rules would actually help triage — worth
revisiting with real ticket data, not guessed at now.
