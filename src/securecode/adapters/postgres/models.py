from datetime import datetime
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_evidence: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationship to evaluations
    evaluations: Mapped[list["EvaluationRecord"]] = relationship(back_populates="evidence")

class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=True) # Migration safety
    rule_version: Mapped[int] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_records.id"), nullable=False)
    
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_repository: Mapped[str] = mapped_column(String(255), nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship to evidence
    evidence: Mapped["EvidenceRecord"] = relationship(back_populates="evaluations")
