"""
Module: tickets
File responsibility (repository.py): all queries for the tickets table.
Every method is tenant-scoped.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tickets.models import Ticket, TicketStatus


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def get_by_id_for_tenant(self, ticket_id: uuid.UUID, tenant_id: uuid.UUID) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id))

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Ticket]:
        return list(
            self.db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id).order_by(Ticket.created_at.desc()))
        )

    def list_for_conversation(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> list[Ticket]:
        return list(
            self.db.scalars(
                select(Ticket)
                .where(Ticket.conversation_id == conversation_id, Ticket.tenant_id == tenant_id)
                .order_by(Ticket.created_at.desc())
            )
        )

    def update_status(self, ticket: Ticket, status: TicketStatus) -> Ticket:
        ticket.status = status
        self.db.add(ticket)
        self.db.flush()
        return ticket
