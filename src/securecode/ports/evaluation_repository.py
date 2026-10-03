from typing import Protocol, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence

@dataclass
class PersistedEvaluation:
    id: UUID
    control_id: str
    rule_id: Optional[str]
    rule_version: Optional[int]
    status: EvaluationStatus
    collected_at: datetime
    evaluated_at: datetime
    evidence_id: UUID
    source_type: str
    source_repository: str
    source_branch: str
    reconstructed_evidence: Union[GH001Evidence, GH002Evidence]

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
        rule_id: Optional[str] = None,
        rule_version: Optional[int] = None,
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
        rule_id: Optional[str] = None,
        rule_version: Optional[int] = None,
    ) -> None:
        """Save a GH-002 evaluation and its normalized evidence atomically."""
        ...

    def get_evaluation(self, evaluation_id: UUID) -> Optional[PersistedEvaluation]:
        """Retrieve an evaluation and reconstruct its evidence."""
        ...

