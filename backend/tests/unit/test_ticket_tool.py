"""Unit tests for the create_ticket tool's input schema and delegation
to TicketService -- no graph, no HTTP."""
import uuid

import pytest
from pydantic import ValidationError

from app.modules.agent.tools import CreateTicketInput, create_ticket_tool
from app.modules.conversations.models import Conversation, ConversationStatus
from app.modules.knowledge_base.models import KnowledgeBase


def test_create_ticket_input_requires_tenant_and_conversation_ids():
    with pytest.raises(ValidationError):
        CreateTicketInput(title="x", description="y")  # missing tenant_id, conversation_id


def test_create_ticket_input_defaults_priority_to_medium():
    payload = CreateTicketInput(
        tenant_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        customer_identifier="c@example.com",
        title="Cannot log in",
        description="Customer reports login failures since yesterday.",
    )
    assert payload.priority.value == "medium"


def test_create_ticket_tool_persists_a_real_ticket(db_session, tenant_a):
    tenant, user = tenant_a
    kb = KnowledgeBase(tenant_id=tenant.id, name="Docs")
    db_session.add(kb)
    db_session.flush()
    conversation = Conversation(
        tenant_id=tenant.id, knowledge_base_id=kb.id, customer_identifier="c@example.com", status=ConversationStatus.OPEN
    )
    db_session.add(conversation)
    db_session.commit()

    ticket = create_ticket_tool(
        db_session,
        CreateTicketInput(
            tenant_id=tenant.id,
            conversation_id=conversation.id,
            customer_identifier="c@example.com",
            title="Charged twice",
            description="Customer reports a duplicate charge on their last invoice.",
        ),
    )

    assert ticket.id is not None
    assert ticket.status.value == "open"
    assert ticket.tenant_id == tenant.id
