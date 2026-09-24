"""
Module: tickets
File responsibility (schemas.py): API request/response models.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tickets.models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    """For manual, staff-initiated ticket creation. The AI agent's own
    ticket creation path (modules/agent/tools.py: create_ticket_tool)
    does not go through this schema -- it's invoked internally by
    ConversationService, not over HTTP -- but both paths ultimately call
    TicketService.create_ticket, so validation rules stay in one place."""

    conversation_id: uuid.UUID
    customer_identifier: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    customer_identifier: str
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
