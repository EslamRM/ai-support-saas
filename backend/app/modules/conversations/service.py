"""
Module: conversations
File responsibility (service.py): conversation lifecycle + the turn-by-
turn orchestration that ties persistence to the agent graph.

send_message() is the integration point between Phase 5 (the agent
graph) and Phase 6 (persistence): load bounded history -> persist the
user's message -> invoke the graph -> persist the assistant's response
with its routing metadata -> return both.

KNOWN GAP, DOCUMENTED: these endpoints require a staff JWT (CurrentUser),
the same as the rest of the dashboard API. The real end customer talking
to a chat widget is NOT a tenant User and shouldn't need a staff account
-- a production system needs a separate, public, KB-scoped auth
mechanism for the widget (e.g. a short-lived embed token scoped to one
knowledge_base_id, issued when the widget loads, with no access to
anything else in the tenant). That's a real piece of design work not
included in this phase -- see docs/architecture.md system boundaries.
For now, this API is sufficient for admin-driven testing of the bot
(e.g. a support agent trying out their own knowledge base) and for the
dashboard's conversation-review view (Phase 8).
"""
import time
import uuid

import structlog

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.logging import set_conversation_id
from app.modules.agent.graph import build_agent_graph
from app.modules.agent.llm import get_chat_model
from app.modules.conversations.context import build_bounded_history
from app.modules.conversations.models import Conversation, ConversationStatus, Message, MessageRole
from app.modules.conversations.repository import ConversationRepository, MessageRepository
from app.modules.knowledge_base.service import KnowledgeBaseService


logger = structlog.get_logger(__name__)


class ConversationNotFoundError(DomainError):
    pass


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.kb_service = KnowledgeBaseService(db)

    def start_conversation(
        self, *, tenant_id: uuid.UUID, knowledge_base_id: uuid.UUID, customer_identifier: str
    ) -> Conversation:
        # Same IDOR check as document upload (Phase 4): confirms the KB
        # exists AND belongs to this tenant before creating a
        # conversation against it.
        self.kb_service.get_or_404(knowledge_base_id, tenant_id)

        conversation = Conversation(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            customer_identifier=customer_identifier,
            status=ConversationStatus.OPEN,
        )
        self.conversations.create(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_or_404(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> Conversation:
        conversation = self.conversations.get_by_id_for_tenant(conversation_id, tenant_id)
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found")
        return conversation

    def get_with_messages(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[Conversation, list[Message]]:
        conversation = self.get_or_404(conversation_id, tenant_id)
        messages = self.messages.list_all_for_conversation(conversation_id, tenant_id)
        return conversation, messages

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Conversation]:
        return self.conversations.list_for_tenant(tenant_id)

    def send_message(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str,
        agent_graph_factory=None,
    ) -> Message:
        """agent_graph_factory is injectable so tests can pass a factory
        that returns a graph wired to fake providers, without this
        service needing to know anything about VectorStore/ChatModel
        itself. Resolved to the module-level build_agent_graph INSIDE the
        method body (not as a bound default parameter value) specifically
        so tests can monkeypatch this module's `build_agent_graph` name
        and have it take effect -- a default parameter value would be
        bound once at import time and wouldn't see the patch."""
        factory = agent_graph_factory or build_agent_graph
        conversation = self.get_or_404(conversation_id, tenant_id)
        set_conversation_id(str(conversation_id))
        turn_started = time.perf_counter()
        logger.info("agent.execution.started", knowledge_base_id=str(conversation.knowledge_base_id))

        # Bounded history from BEFORE this turn -- the message we're
        # about to add is passed separately as "question", not folded
        # into history (see modules/agent/state.py).
        prior_messages = self.messages.list_recent_for_conversation(conversation_id, tenant_id)
        history = build_bounded_history(prior_messages)

        user_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
        )
        self.messages.add(user_message)
        self.db.commit()

        graph = factory()
        try:
            result = graph.invoke(
            {
                "tenant_id": str(tenant_id),
                "knowledge_base_id": str(conversation.knowledge_base_id),
                "question": content,
                "history": history,
            }
            )
        except Exception:
            logger.exception("agent.execution.failed", latency_ms=round((time.perf_counter() - turn_started) * 1000, 2))
            raise

        agent_latency_ms = round((time.perf_counter() - turn_started) * 1000, 2)
        logger.info(
            "agent.execution.completed",
            route=result.get("route"),
            retrieved_chunk_count=len(result.get("retrieved_chunks", [])),
            latency_ms=agent_latency_ms,
        )

        agent_metadata = {
            "route": result.get("route"),
            "grounded": result.get("grounded"),
            "confidence": result.get("confidence"),
            "needs_retrieval": result.get("needs_retrieval"),
            "retrieved_chunk_count": len(result.get("retrieved_chunks", [])),
            "latency_ms": agent_latency_ms,
            "llm_latency_ms": result.get("llm_latency_ms"),
            "prompt_tokens": result.get("prompt_tokens"),
            "completion_tokens": result.get("completion_tokens"),
            "total_tokens": result.get("total_tokens"),
        }

        if result.get("route") == "handoff":
            # Deterministic tool invocation, not an LLM function-call
            # choice -- quality_check already decided a ticket is needed;
            # summarize_for_ticket only writes a good title/description
            # for it. See modules/agent/tools.py's module docstring for
            # the full "why deterministic, not LLM-chosen" reasoning.
            #
            # Imported here, not at module top, to avoid a circular
            # import: tickets/service.py imports ConversationService for
            # its own IDOR check, so this module can't import
            # tickets-module code at import time -- same pattern already
            # used for process_document_task in documents/service.py.
            from app.modules.agent.tools import CreateTicketInput, create_ticket_tool

            chat_model = get_chat_model()
            summary = chat_model.summarize_for_ticket(question=content, answer=result["answer"], history=history)
            ticket = create_ticket_tool(
                self.db,
                CreateTicketInput(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    customer_identifier=conversation.customer_identifier,
                    title=summary.title,
                    description=summary.description,
                ),
                commit=False,
            )
            logger.info("agent.ticket_created", ticket_id=str(ticket.id))
            agent_metadata["ticket_id"] = str(ticket.id)
            # The tool uses commit=False here. The ticket and assistant
            # message are committed together below, avoiding a partial
            # handoff where a ticket exists without its assistant record.

        assistant_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=result["answer"],
            agent_metadata=agent_metadata,
        )
        self.messages.add(assistant_message)
        self.db.commit()
        self.db.refresh(assistant_message)

        return assistant_message
