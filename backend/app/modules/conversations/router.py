"""
Module: conversations
File responsibility (router.py): conversation + message endpoints.
See service.py's docstring for the known gap on customer-facing auth --
these routes currently require the same staff JWT as the rest of the
dashboard API.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.conversations.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessagesResponse,
    MessageCreate,
    MessageResponse,
)
from app.modules.conversations.service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationResponse:
    service = ConversationService(db)
    conversation = service.start_conversation(
        tenant_id=user.tenant_id,
        knowledge_base_id=payload.knowledge_base_id,
        customer_identifier=payload.customer_identifier,
    )
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ConversationResponse]:
    service = ConversationService(db)
    return [ConversationResponse.model_validate(c) for c in service.list_for_tenant(user.tenant_id)]


@router.get("/{conversation_id}", response_model=ConversationWithMessagesResponse)
def get_conversation(
    conversation_id: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationWithMessagesResponse:
    service = ConversationService(db)
    conversation, messages = service.get_with_messages(uuid.UUID(conversation_id), user.tenant_id)
    return ConversationWithMessagesResponse(
        **ConversationResponse.model_validate(conversation).model_dump(),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
def send_message(
    conversation_id: str,
    payload: MessageCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    service = ConversationService(db)
    assistant_message = service.send_message(
        tenant_id=user.tenant_id,
        conversation_id=uuid.UUID(conversation_id),
        content=payload.content,
    )
    return MessageResponse.model_validate(assistant_message)
