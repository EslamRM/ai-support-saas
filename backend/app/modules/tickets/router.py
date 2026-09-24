"""
Module: tickets
File responsibility (router.py): staff-facing ticket endpoints -- manual
creation, listing, and status updates. The AI agent's own ticket
creation (on handoff) does not go through HTTP at all -- see
modules/agent/tools.py and modules/conversations/service.py.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, require_role
from app.db.session import get_db
from app.modules.auth.models import User, UserRole
from app.modules.tickets.schemas import TicketCreate, TicketResponse, TicketStatusUpdate
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    payload: TicketCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.create_ticket(
        tenant_id=user.tenant_id,
        conversation_id=payload.conversation_id,
        customer_identifier=payload.customer_identifier,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )
    return TicketResponse.model_validate(ticket)


@router.get("", response_model=list[TicketResponse])
def list_tickets(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[TicketResponse]:
    service = TicketService(db)
    return [TicketResponse.model_validate(t) for t in service.list_for_tenant(user.tenant_id)]


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.get_or_404(uuid.UUID(ticket_id), user.tenant_id)
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: str,
    payload: TicketStatusUpdate,
    # Status changes (e.g. marking resolved/closed) require admin+,
    # unlike read/create -- an agent-level staff account shouldn't be
    # able to silently close out another agent's ticket. See
    # core/dependencies.require_role.
    user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    service = TicketService(db)
    ticket = service.update_status(uuid.UUID(ticket_id), user.tenant_id, payload.status)
    return TicketResponse.model_validate(ticket)
