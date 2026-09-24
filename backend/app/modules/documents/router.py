"""
Module: documents
File responsibility (router.py): document upload + listing endpoints.
Upload uses multipart/form-data (FastAPI's UploadFile), not a JSON body,
since it's carrying binary file content.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.core.config import settings
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.documents.schemas import DocumentResponse
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=202)
async def upload_document(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    knowledge_base_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    # 202 Accepted, not 201 Created: the Document row exists, but
    # processing hasn't finished -- the response reflects PENDING status,
    # and the client is expected to poll GET /documents/{id} (or
    # GET /knowledge-bases/{kb_id}/documents, added below) for status.
    # Do not trust Content-Length or filename alone; read with a hard cap so a
    # client cannot make the API allocate an unbounded request body.
    raw_content = await file.read(settings.max_upload_size_bytes + 1)
    service = DocumentService(db)
    document = service.upload_document(
        tenant_id=user.tenant_id,
        knowledge_base_id=uuid.UUID(knowledge_base_id),
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        raw_content=raw_content,
    )
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    service = DocumentService(db)
    document = service.get_or_404(uuid.UUID(document_id), user.tenant_id)
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    knowledge_base_id: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentResponse]:
    service = DocumentService(db)
    documents = service.list_for_knowledge_base(uuid.UUID(knowledge_base_id), user.tenant_id)
    return [DocumentResponse.model_validate(d) for d in documents]
