from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence


@dataclass
class PersistedEvaluation:
    id: UUID
    control_id: str
    rule_id: str | None
    rule_version: int | None
    status: EvaluationStatus
    collected_at: datetime
    evaluated_at: datetime
    evidence_id: UUID
    source_type: str
    source_repository: str
    source_branch: str
    reconstructed_evidence: GH001Evidence | GH002Evidence | GH003Evidence
    requested_by_user_id: UUID | None = None

class EvaluationRepository(Protocol):
    """Port for persisting evaluations independent of storage mechanism."""
    
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
        """Save a GH-001 evaluation and its normalized evidence atomically."""
        ...
        
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
        """Save a GH-002 evaluation and its normalized evidence atomically."""
        ...

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
        """Save a GH-003 evaluation and its normalized evidence atomically."""
        ...

    def get_evaluation(self, evaluation_id: UUID) -> PersistedEvaluation | None:
        """Retrieve an evaluation and reconstruct its evidence."""
        ...

