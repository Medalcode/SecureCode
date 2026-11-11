from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from securecode.adapters.postgres.models import EvaluationRecord, EvidenceRecord
from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.ports.evaluation_repository import (
    EvaluationRepository,
    PersistedEvaluation,
)


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
        rule_id: str | None = None,
        rule_version: int | None = None,
        requested_by_user_id: UUID | None = None,
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
                rule_id=rule_id,
                rule_version=rule_version,
                status=status.name,
                evaluated_at=evaluated_at,
                evidence_id=evidence_id,
                requested_by_user_id=requested_by_user_id,
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

    def save_gh002_evaluation(
        self,
        evaluation_id: UUID,
        evidence_id: UUID,
        evidence: GH002Evidence,
        status: EvaluationStatus,
        source_repository: str,
        source_branch: str,
        collected_at: datetime,
        evaluated_at: datetime,
        rule_id: str | None = None,
        rule_version: int | None = None,
        requested_by_user_id: UUID | None = None,
    ) -> None:
        """Save GH-002 evidence and evaluation atomically."""
        try:
            raw_evidence = {
                "default_branch": evidence.default_branch,
                "protection_enabled": evidence.protection_enabled,
            }
            
            evidence_record = EvidenceRecord(
                id=evidence_id,
                control_id="GH-002",
                evidence_hash=evidence.canonical_hash(),
                raw_evidence=raw_evidence,
                collected_at=collected_at
            )
            
            evaluation_record = EvaluationRecord(
                id=evaluation_id,
                control_id="GH-002",
                rule_id=rule_id,
                rule_version=rule_version,
                status=status.name,
                evaluated_at=evaluated_at,
                evidence_id=evidence_id,
                requested_by_user_id=requested_by_user_id,
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

    def save_gh003_evaluation(
        self,
        evaluation_id: UUID,
        evidence_id: UUID,
        evidence: GH003Evidence,
        status: EvaluationStatus,
        source_repository: str,
        source_branch: str,
        collected_at: datetime,
        evaluated_at: datetime,
        rule_id: str | None = None,
        rule_version: int | None = None,
        requested_by_user_id: UUID | None = None,
    ) -> None:
        """Save signed-commit enforcement evidence atomically."""
        try:
            evidence_record = EvidenceRecord(
                id=evidence_id,
                control_id="GH-003",
                evidence_hash=evidence.canonical_hash(),
                raw_evidence={
                    "branch": evidence.branch,
                    "required_signatures_enabled": evidence.required_signatures_enabled,
                },
                collected_at=collected_at,
            )
            evaluation_record = EvaluationRecord(
                id=evaluation_id,
                control_id="GH-003",
                rule_id=rule_id,
                rule_version=rule_version,
                status=status.name,
                evaluated_at=evaluated_at,
                evidence_id=evidence_id,
                requested_by_user_id=requested_by_user_id,
                source_type="GitHub",
                source_repository=source_repository,
                source_branch=source_branch,
            )
            self._session.add(evidence_record)
            self._session.add(evaluation_record)
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RuntimeError(f"Failed to persist evaluation: {e}") from e

    def get_evaluation(self, evaluation_id: UUID) -> PersistedEvaluation | None:
        """Retrieve an evaluation and reconstruct the immutable domain evidence."""
        record = self._session.query(EvaluationRecord).filter_by(id=evaluation_id).first()
        if not record:
            return None
            
        evidence_record = record.evidence
        raw = evidence_record.raw_evidence
        
        # Reconstruct domain model safely based on control_id
        reconstructed_evidence: GH001Evidence | GH002Evidence | GH003Evidence
        if record.control_id == "GH-001":
            reconstructed_evidence = GH001Evidence(
                required_review_approvals=raw.get("required_review_approvals"),
                dismiss_stale_reviews=raw.get("dismiss_stale_reviews")
            )
        elif record.control_id == "GH-002":
            reconstructed_evidence = GH002Evidence(
                default_branch=raw.get("default_branch", ""),
                protection_enabled=raw.get("protection_enabled")
            )
        elif record.control_id == "GH-003":
            reconstructed_evidence = GH003Evidence(
                branch=raw.get("branch", record.source_branch),
                required_signatures_enabled=raw.get("required_signatures_enabled"),
            )
        else:
            raise ValueError(f"Unknown control_id {record.control_id} in database")
        
        return PersistedEvaluation(
            id=record.id,
            control_id=record.control_id,
            rule_id=record.rule_id,
            rule_version=record.rule_version,
            status=EvaluationStatus(record.status),
            collected_at=evidence_record.collected_at,
            evaluated_at=record.evaluated_at,
            evidence_id=record.evidence_id,
            requested_by_user_id=record.requested_by_user_id,
            source_type=record.source_type,
            source_repository=record.source_repository,
            source_branch=record.source_branch,
            reconstructed_evidence=reconstructed_evidence
        )
