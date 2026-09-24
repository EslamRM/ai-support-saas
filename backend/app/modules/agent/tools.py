"""
Module: agent
File responsibility (tools.py): the create_ticket tool.

IMPORTANT DESIGN DECISION -- this tool is invoked DETERMINISTICALLY by
application code (ConversationService, after the graph returns
route="handoff"), NOT chosen at the LLM's discretion via OpenAI-style
function calling. See docs/tickets.md "Why a deterministic tool, not an
LLM-chosen one" for the full reasoning -- in short: quality_check
(modules/agent/nodes/quality_check.py) already deterministically decides
WHETHER to hand off, using signals the LLM itself produced. Also letting
the LLM independently decide whether to call create_ticket would mean
two decision-makers for one decision, which could disagree -- exactly
the "unnecessarily autonomous agent" failure mode this project avoids
elsewhere (classify_intent, quality_check). The LLM's role here is
narrower and safer: modules/agent/llm.py's summarize_for_ticket writes a
good title/description FROM a conversation that's already been decided
to need a ticket -- it doesn't decide whether one should exist.

Every tool in this file: has an explicit Pydantic input schema (the
caller can't pass anything the schema doesn't allow), delegates the
actual database write to the OWNING module's service
(modules/tickets/service.py -- tenant/IDOR checks live there, not
duplicated here), and logs its invocation. There is no code path here
that lets an LLM directly touch the database or execute arbitrary code.
"""
import structlog
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.modules.tickets.models import Ticket, TicketPriority
from app.modules.tickets.service import TicketService

logger = structlog.get_logger(__name__)


class CreateTicketInput(BaseModel):
    """The tool's explicit input schema. tenant_id and conversation_id
    are required, non-optional fields -- there is no way to construct a
    valid CreateTicketInput without them, which is what makes "the LLM
    forgot to scope this to a tenant" structurally impossible rather
    than a runtime check that could be skipped."""

    tenant_id: uuid.UUID
    conversation_id: uuid.UUID
    customer_identifier: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM


def create_ticket_tool(db: Session, payload: CreateTicketInput, *, commit: bool = True) -> Ticket:
    logger.info(
        "agent.tool.create_ticket",
        tenant_id=str(payload.tenant_id),
        conversation_id=str(payload.conversation_id),
        priority=payload.priority.value,
        commit=commit,
    )
    service = TicketService(db)
    return service.create_ticket(
        tenant_id=payload.tenant_id,
        conversation_id=payload.conversation_id,
        customer_identifier=payload.customer_identifier,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        commit=commit,
    )
