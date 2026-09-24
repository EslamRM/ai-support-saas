"""
Module: tenants
File responsibility (router.py): tenant-facing endpoints. Tenant
CREATION happens through /auth/register (signup creates tenant + owner
together) -- this router is for querying/managing an EXISTING tenant
once authenticated.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.schemas import TenantResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> TenantResponse:
    tenant = TenantRepository(db).get_by_id(user.tenant_id)
    return TenantResponse.model_validate(tenant)
