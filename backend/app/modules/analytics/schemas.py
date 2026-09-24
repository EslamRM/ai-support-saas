"""
Module: analytics
File responsibility (schemas.py): the aggregate summary shape returned
by GET /analytics. Deliberately a small, fixed set of counts -- not a
generic "query builder" API. See service.py for why.
"""
from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    conversation_count: int
    message_count: int
    ticket_count: int
    tickets_by_status: dict[str, int]
    handoff_rate: float | None  # fraction of assistant messages routed to handoff, 0-1
    average_confidence: float | None  # across assistant messages that have a confidence score
