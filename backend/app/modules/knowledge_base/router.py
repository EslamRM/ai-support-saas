"""
Module: knowledge_base
File responsibility (router.py): knowledge base CRUD endpoints.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.knowledge_base.schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from app.modules.knowledge_base.service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeBaseResponse:
    service = KnowledgeBaseService(db)
    kb = service.create(user.tenant_id, payload.name, payload.description)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("", response_model=list[KnowledgeBaseResponse])
def list_knowledge_bases(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    service = KnowledgeBaseService(db)
    return [KnowledgeBaseResponse.model_validate(kb) for kb in service.list_for_tenant(user.tenant_id)]


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    kb_id: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeBaseResponse:
    service = KnowledgeBaseService(db)
    kb = service.get_or_404(uuid.UUID(kb_id), user.tenant_id)
    return KnowledgeBaseResponse.model_validate(kb)
