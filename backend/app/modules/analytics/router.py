"""
Module: analytics
File responsibility (router.py): GET /analytics -- the dashboard's
summary metrics endpoint.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.analytics.schemas import AnalyticsSummary
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsSummary)
def get_analytics_summary(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> AnalyticsSummary:
    service = AnalyticsService(db)
    return service.get_summary(user.tenant_id)
