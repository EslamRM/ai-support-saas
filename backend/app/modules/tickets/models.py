"""
Module: tickets
Purpose: support tickets, created either by a human agent (manual POST
/tickets) or by the AI agent's handoff tool (see modules/agent/tools.py)
when quality_check routes a conversation to "handoff".
"""
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantScopedBase


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Ticket(TenantScopedBase):
    __tablename__ = "tickets"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # DESIGN DECISION -- priority always defaults to MEDIUM in v1; there is
    # no automatic urgency classification (e.g. "charged twice" ranked
    # higher than "how do I change my email"). A content-based priority
    # classifier is a real, useful improvement but adds another
    # LLM-judgment surface for a v1 that doesn't yet have data on whether
    # simplistic keyword rules would even help -- deferred, not
    # forgotten. See docs/tickets.md.
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"), nullable=False, default=TicketPriority.MEDIUM
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"), nullable=False, default=TicketStatus.OPEN
    )
