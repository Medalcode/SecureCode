from uuid import uuid4
from datetime import datetime, timezone

from securecode.ports.evaluation_repository import EvaluationRepository, PersistedEvaluation
from securecode.engine.evaluator import evaluate_gh001
from securecode.adapters.github import get_gh001_evidence

def evaluate_and_store_gh001(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    repository: EvaluationRepository
) -> PersistedEvaluation:
    """
    Orchestrates evidence acquisition, evaluation, and persistence.
    """
    collected_at = datetime.now(timezone.utc)
    
    # Acquire Evidence
    evidence = get_gh001_evidence(owner, repo, branch, token)
    
    evaluated_at = datetime.now(timezone.utc)
    
    # Evaluate deterministically
    status = evaluate_gh001(evidence)
    
    # Generate IDs
    evaluation_id = uuid4()
    evidence_id = uuid4()
    
    # Persist
    repository.save_gh001_evaluation(
        evaluation_id=evaluation_id,
        evidence_id=evidence_id,
        evidence=evidence,
        status=status,
        source_repository=f"{owner}/{repo}",
        source_branch=branch,
        collected_at=collected_at,
        evaluated_at=evaluated_at
    )
    
    # Retrieve to return a reconstructed instance ensuring it was safely stored
    persisted = repository.get_evaluation(evaluation_id)
    if not persisted:
        raise RuntimeError("Evaluation was saved but could not be retrieved.")
        
    return persisted
