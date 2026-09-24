"""
Module: conversations
File responsibility (repository.py): all queries for conversations and
messages. Every method is tenant-scoped.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.conversations.models import Conversation, Message

# Row-count ceiling applied AT THE QUERY LEVEL, before
# conversations/context.py's token-budget trimming ever runs -- two
# independent bounds (see context.py's docstring for why). This one
# exists so a conversation with thousands of turns doesn't get fully
# loaded into memory just to immediately discard most of it.
MAX_MESSAGES_LOADED_FOR_CONTEXT = 50


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get_by_id_for_tenant(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> Conversation | None:
        return self.db.scalar(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Conversation]:
        return list(
            self.db.scalars(
                select(Conversation)
                .where(Conversation.tenant_id == tenant_id)
                .order_by(Conversation.created_at.desc())
            )
        )


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message

    def list_all_for_conversation(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Message]:
        """Full history, oldest-first -- for GET /conversations/{id}
        (a human reading the transcript), NOT for building LLM context.
        Use list_recent_for_conversation for that."""
        return list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.tenant_id == tenant_id)
                .order_by(Message.created_at.asc())
            )
        )

    def list_recent_for_conversation(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Message]:
        """Bounded by MAX_MESSAGES_LOADED_FOR_CONTEXT, returned oldest-
        first. This is the DB-level half of the two-layer context bound
        -- see conversations/context.py for the token-level half."""
        rows = self.db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.tenant_id == tenant_id)
            .order_by(Message.created_at.desc())
            .limit(MAX_MESSAGES_LOADED_FOR_CONTEXT)
        )
        return list(reversed(list(rows)))
