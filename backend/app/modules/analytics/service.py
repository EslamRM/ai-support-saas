"""
Module: analytics
File responsibility (service.py): assembles AnalyticsSummary from the
repository's raw counts.

DESIGN DECISION -- one fixed summary endpoint, not a generic query/report
builder. A tenant dashboard needs "how many conversations/tickets, what's
our handoff rate" today; a flexible ad-hoc analytics query API is a much
bigger feature (and a much bigger security surface -- arbitrary
aggregation queries over tenant data are exactly the kind of thing that's
easy to get tenant-isolation wrong on) with no current requirement
driving it. Add fields here as concrete metrics are needed, rather than
building a generic engine speculatively.
"""
import uuid

from sqlalchemy.orm import Session

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import AnalyticsSummary


class AnalyticsService:
    def __init__(self, db: Session):
        self.repo = AnalyticsRepository(db)

    def get_summary(self, tenant_id: uuid.UUID) -> AnalyticsSummary:
        assistant_messages = self.repo.assistant_messages(tenant_id)

        confidences = [
            m.agent_metadata["confidence"]
            for m in assistant_messages
            if m.agent_metadata and m.agent_metadata.get("confidence") is not None
        ]
        handoffs = [
            m for m in assistant_messages if m.agent_metadata and m.agent_metadata.get("route") == "handoff"
        ]

        return AnalyticsSummary(
            conversation_count=self.repo.conversation_count(tenant_id),
            message_count=self.repo.message_count(tenant_id),
            ticket_count=self.repo.ticket_count(tenant_id),
            tickets_by_status=self.repo.tickets_by_status(tenant_id),
            handoff_rate=(len(handoffs) / len(assistant_messages)) if assistant_messages else None,
            average_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )
