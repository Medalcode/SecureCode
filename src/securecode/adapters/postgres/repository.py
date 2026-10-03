from typing import Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from securecode.ports.evaluation_repository import EvaluationRepository, PersistedEvaluation
from securecode.models.gh001 import GH001Evidence
from securecode.engine.evaluator import EvaluationStatus
from securecode.adapters.postgres.models import EvaluationRecord, EvidenceRecord

class PostgresEvaluationRepository(EvaluationRepository):
    """PostgreSQL implementation of the EvaluationRepository using SQLAlchemy."""
    
    def __init__(self, session: Session):
        self._session = session
        
    def save_gh001_evaluation(
        self,
        evaluation_id: UUID,
        evidence_id: UUID,
        evidence: GH001Evidence,
        status: EvaluationStatus,
        source_repository: str,
        source_branch: str,
        collected_at: datetime,
        evaluated_at: datetime,
    ) -> None:
        """Save evidence and evaluation atomically."""
        try:
            # Construct raw evidence dictionary carefully allowing nulls/None
            raw_evidence = {
                "required_review_approvals": evidence.required_review_approvals,
                "dismiss_stale_reviews": evidence.dismiss_stale_reviews,
            }
            
            evidence_record = EvidenceRecord(
                id=evidence_id,
                control_id="GH-001",
                evidence_hash=evidence.canonical_hash(),
                raw_evidence=raw_evidence,
                collected_at=collected_at
            )
            
            evaluation_record = EvaluationRecord(
                id=evaluation_id,
                control_id="GH-001",
                status=status.name,
                evaluated_at=evaluated_at,
                evidence_id=evidence_id,
                source_type="GitHub",
                source_repository=source_repository,
                source_branch=source_branch
            )
            
            self._session.add(evidence_record)
            self._session.add(evaluation_record)
            self._session.commit()
            
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RuntimeError(f"Failed to persist evaluation: {e}") from e

    def get_evaluation(self, evaluation_id: UUID) -> Optional[PersistedEvaluation]:
        """Retrieve an evaluation and reconstruct the immutable domain evidence."""
        record = self._session.query(EvaluationRecord).filter_by(id=evaluation_id).first()
        if not record:
            return None
            
        evidence_record = record.evidence
        raw = evidence_record.raw_evidence
        
        # Reconstruct domain model safely
        reconstructed_evidence = GH001Evidence(
            required_review_approvals=raw.get("required_review_approvals"),
            dismiss_stale_reviews=raw.get("dismiss_stale_reviews")
        )
        
        return PersistedEvaluation(
            id=record.id,
            control_id=record.control_id,
            status=EvaluationStatus(record.status),
            evaluated_at=record.evaluated_at,
            evidence_id=record.evidence_id,
            source_type=record.source_type,
            source_repository=record.source_repository,
            source_branch=record.source_branch,
            reconstructed_evidence=reconstructed_evidence
        )
