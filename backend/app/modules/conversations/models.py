"""
Module: conversations
Purpose: Conversation + Message persistence.

DESIGN DECISION -- customer_identifier is a plain string (e.g. an email
or an external customer id the tenant's own system uses), NOT a foreign
key to a Customer table. There is no Customer entity in v1: the end
customer talking to the widget is not a tenant User (tenant Users are
staff/dashboard accounts -- see modules/auth/models.py) and doesn't need
an account for this product to work. A real Customer entity (with its
own history across conversations, contact info, etc.) is a natural
future addition once there's a product requirement for it (e.g. a
per-customer conversation history view) -- not built ahead of that need.
"""
import enum
import uuid

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantScopedBase


class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Conversation(TenantScopedBase):
    __tablename__ = "conversations"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"), nullable=False, default=ConversationStatus.OPEN
    )


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(TenantScopedBase):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Agent metadata for assistant messages only (route/grounded/confidence
    # from AgentState -- see modules/agent/state.py). NULL for user
    # messages. Using SQLAlchemy's generic JSON type (not Postgres JSONB)
    # so this works identically against SQLite in tests -- same
    # cross-dialect reasoning as db/base.py's Uuid columns. Lets the
    # dashboard (Phase 8) show WHY an answer was routed to handoff
    # without re-running the agent.
    agent_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
