"""
Module: analytics
File responsibility (repository.py): aggregate COUNT/AVG queries across
conversations, messages, and tickets. Every query is tenant-scoped, same
as every other repository in this codebase.

DESIGN DECISION -- handoff_rate and average_confidence are computed by
reading agent_metadata (a JSON column) out of Message rows in Python,
not with a SQL aggregate over JSON fields. This works fine at the
current expected data volume and keeps the query portable across SQLite
(tests) and Postgres (production) without relying on either engine's
JSON-specific SQL functions. Revisit with a materialized/denormalized
column (or a real analytics store) if message volume ever makes
loading all assistant messages into Python for this computation slow --
see docs/scaling.md.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.conversations.models import Conversation, Message, MessageRole
from app.modules.tickets.models import Ticket, TicketStatus


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def conversation_count(self, tenant_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.tenant_id == tenant_id)
        ) or 0

    def message_count(self, tenant_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Message).where(Message.tenant_id == tenant_id)
        ) or 0

    def ticket_count(self, tenant_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)
        ) or 0

    def tickets_by_status(self, tenant_id: uuid.UUID) -> dict[str, int]:
        rows = self.db.execute(
            select(Ticket.status, func.count())
            .where(Ticket.tenant_id == tenant_id)
            .group_by(Ticket.status)
        ).all()
        counts = {status.value: 0 for status in TicketStatus}
        for status, count in rows:
            counts[status.value] = count
        return counts

    def assistant_messages(self, tenant_id: uuid.UUID) -> list[Message]:
        return list(
            self.db.scalars(
                select(Message).where(Message.tenant_id == tenant_id, Message.role == MessageRole.ASSISTANT)
            )
        )
