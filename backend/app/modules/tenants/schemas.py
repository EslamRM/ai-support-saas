"""
Module: tenants
File responsibility (schemas.py): API request/response models.
"""
import uuid

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
