"""
Module: tickets
File responsibility (service.py): ticket business logic. This is the
SINGLE creation path for a Ticket row -- both the staff-facing router
(manual creation) and the AI agent's tool (modules/agent/tools.py) call
create_ticket() here, so validation and tenant-scoping rules live in
exactly one place regardless of who's creating the ticket.
"""
import uuid

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.modules.conversations.service import ConversationService
from app.modules.tickets.models import Ticket, TicketPriority, TicketStatus
from app.modules.tickets.repository import TicketRepository


logger = structlog.get_logger(__name__)


class TicketNotFoundError(DomainError):
    pass


class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TicketRepository(db)
        self.conversations = ConversationService(db)

    def create_ticket(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        customer_identifier: str,
        title: str,
        description: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        commit: bool = True,
    ) -> Ticket:
        # Confirms the conversation exists AND belongs to this tenant --
        # the same IDOR check pattern as document upload (Phase 4) and
        # starting a conversation (Phase 6). Without this, a caller could
        # attach a ticket to another tenant's conversation_id.
        self.conversations.get_or_404(conversation_id, tenant_id)

        ticket = Ticket(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            customer_identifier=customer_identifier,
            title=title,
            description=description,
            priority=priority,
            status=TicketStatus.OPEN,
        )
        self.repo.create(ticket)
        if commit:
            self.db.commit()
            self.db.refresh(ticket)
        else:
            self.db.flush()
        logger.info(
            "ticket.created",
            priority=priority.value,
            commit=commit,
        )
        return ticket

    def get_or_404(self, ticket_id: uuid.UUID, tenant_id: uuid.UUID) -> Ticket:
        ticket = self.repo.get_by_id_for_tenant(ticket_id, tenant_id)
        if ticket is None:
            raise TicketNotFoundError("Ticket not found")
        return ticket

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Ticket]:
        return self.repo.list_for_tenant(tenant_id)

    def list_for_conversation(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Ticket]:
        return self.repo.list_for_conversation(conversation_id, tenant_id)

    def update_status(self, ticket_id: uuid.UUID, tenant_id: uuid.UUID, status: TicketStatus) -> Ticket:
        ticket = self.get_or_404(ticket_id, tenant_id)
        self.repo.update_status(ticket, status)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket
