"""
Module: conversations
File responsibility (schemas.py): API request/response models.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.conversations.models import ConversationStatus, MessageRole


class ConversationCreate(BaseModel):
    knowledge_base_id: uuid.UUID
    customer_identifier: str = Field(min_length=1, max_length=255)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    agent_metadata: dict | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    customer_identifier: str
    status: ConversationStatus
    created_at: datetime


class ConversationWithMessagesResponse(ConversationResponse):
    messages: list[MessageResponse]
