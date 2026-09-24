"""
Module: documents
File responsibility (schemas.py): API request/response models.
Upload itself uses FastAPI's UploadFile (multipart/form-data), not a
Pydantic body -- see router.py.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.documents.models import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    content_type: str
    status: DocumentStatus
    error_message: str | None
    chunk_count: int
    created_at: datetime
