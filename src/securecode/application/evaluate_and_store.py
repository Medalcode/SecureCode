from datetime import UTC, datetime
from uuid import UUID, uuid4

from securecode.adapters.github import (
    get_gh001_evidence,
    get_gh002_evidence,
    get_gh003_evidence,
)
from securecode.engine.evaluator import (
    evaluate_gh001,
    evaluate_gh002,
    evaluate_gh003,
    get_rule_definition,
)
from securecode.ports.evaluation_repository import (
    EvaluationRepository,
    PersistedEvaluation,
)


def evaluate_and_store_gh001(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    repository: EvaluationRepository,
    requested_by_user_id: UUID | None = None
) -> PersistedEvaluation:
    """
    Orchestrates evidence acquisition, evaluation, and persistence.
    """
    collected_at = datetime.now(UTC)
    evidence = get_gh001_evidence(owner, repo, branch, token)
    evaluated_at = datetime.now(UTC)
    
    rule_def = get_rule_definition("GH-001.json")
    status = evaluate_gh001(evidence, rule_def)
    
    evaluation_id = uuid4()
    evidence_id = uuid4()
    
    repository.save_gh001_evaluation(
        evaluation_id=evaluation_id,
        evidence_id=evidence_id,
        evidence=evidence,
        status=status,
        source_repository=f"{owner}/{repo}",
        source_branch=branch,
        collected_at=collected_at,
        evaluated_at=evaluated_at,
        rule_id=rule_def.rule_id,
        rule_version=rule_def.version,
        requested_by_user_id=requested_by_user_id
    )
    
    persisted = repository.get_evaluation(evaluation_id)
    if not persisted:
        raise RuntimeError("Evaluation was saved but could not be retrieved.")
        
    return persisted

def evaluate_and_store_gh002(
    owner: str,
    repo: str,
    token: str,
    repository: EvaluationRepository,
    requested_by_user_id: UUID | None = None
) -> PersistedEvaluation:
    """
    Orchestrates evidence acquisition, evaluation, and persistence for GH-002.
    """
    collected_at = datetime.now(UTC)
    evidence = get_gh002_evidence(owner, repo, token)
    evaluated_at = datetime.now(UTC)
    
    rule_def = get_rule_definition("GH-002.json")
    status = evaluate_gh002(evidence, rule_def)
    
    evaluation_id = uuid4()
    evidence_id = uuid4()
    
    repository.save_gh002_evaluation(
        evaluation_id=evaluation_id,
        evidence_id=evidence_id,
        evidence=evidence,
        status=status,
        source_repository=f"{owner}/{repo}",
        source_branch=evidence.default_branch or "unknown",
        collected_at=collected_at,
        evaluated_at=evaluated_at,
        rule_id=rule_def.rule_id,
        rule_version=rule_def.version,
        requested_by_user_id=requested_by_user_id
    )
    
    persisted = repository.get_evaluation(evaluation_id)
    if not persisted:
        raise RuntimeError("Evaluation was saved but could not be retrieved.")
        
    return persisted


def evaluate_and_store_gh003(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    repository: EvaluationRepository,
    requested_by_user_id: UUID | None = None,
) -> PersistedEvaluation:
    """Acquire, evaluate and persist signed-commit policy evidence."""
    collected_at = datetime.now(UTC)
    evidence = get_gh003_evidence(owner, repo, branch, token)
    evaluated_at = datetime.now(UTC)
    rule_def = get_rule_definition("GH-003.json")
    status = evaluate_gh003(evidence, rule_def)
    evaluation_id, evidence_id = uuid4(), uuid4()
    repository.save_gh003_evaluation(
        evaluation_id=evaluation_id,
        evidence_id=evidence_id,
        evidence=evidence,
        status=status,
        source_repository=f"{owner}/{repo}",
        source_branch=branch,
        collected_at=collected_at,
        evaluated_at=evaluated_at,
        rule_id=rule_def.rule_id,
        rule_version=rule_def.version,
        requested_by_user_id=requested_by_user_id,
    )
    persisted = repository.get_evaluation(evaluation_id)
    if not persisted:
        raise RuntimeError("Evaluation was saved but could not be retrieved.")
    return persisted
