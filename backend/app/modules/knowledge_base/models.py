"""
Module: knowledge_base
File responsibility (models.py): the KnowledgeBase entity -- a named
grouping of documents within a tenant (e.g. one KB per product line).
Documents (modules/documents) always belong to exactly one KnowledgeBase.
"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantScopedBase


class KnowledgeBase(TenantScopedBase):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
