# Design Document: SecureCode Core Domain

## Overview

This document describes the technical design for SecureCode Core Domain - a GRC (Governance, Risk, Compliance) platform for automated security control evaluation.

### Key Features
- **8 SQLAlchemy models** for PostgreSQL persistence
- **Deterministic rule engine** (100% reproducible, no side effects)
- **Property-based testing** for critical logic
- **CI/CD pipeline** with GitHub Actions

### Design Decisions
1. **Deterministic Engine**: No `datetime.now()`, `random()`, or external calls - all timestamps and randomness must come from inputs
2. **INSERT-Only Persistence**: Critical tables (evidence, evaluation, audit_log) never UPDATE or DELETE - new records for changes
3. **Separation of Concerns**: Models, Engine, Adapters, API modules
4. **Property-Based Testing**: Used for rule evaluation logic, determinism verification, round-trip persistence

---

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "API Layer"
        API[GitHub OAuth API]
        REST[REST API Endpoints]
    end
    
    subgraph "Application Layer"
        Auth[AuthService]
        Engine[RuleEngine]
    end
    
    subgraph "Domain Layer"
        Models[SQLAlchemy Models]
        Rules[Rule Definitions]
        Evidence[Evidence Data]
    end
    
    subgraph "Infrastructure Layer"
        DB[(PostgreSQL)]
        Cache[Result Cache]
    end
    
    subgraph "Testing Layer"
        Unit[Unit Tests]
        Property[PBT Tests]
        Integration[Integration Tests]
    end
    
    API --> Auth
    REST --> Auth
    Auth --> Models
    Engine --> Rules
    Engine --> Evidence
    Engine --> Cache
    Models --> DB
    Cache --> DB
    Unit --> Engine
    Property --> Engine
    Integration --> DB
```

### Component Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Auth
    participant Engine
    participant DB
    
    User->>API: GET /evaluations
    API->>Auth: Validate OAuth Token
    Auth->>DB: Query GitHubAccount
    DB-->>Auth: User ID
    
    Auth-->>API: User ID
    API->>Engine: Evaluate Rules for Evidence
    Engine->>DB: SELECT evidence, rules
    DB-->>Engine: Evidence & Rules
    
    Engine->>Engine: Evaluate Rules (deterministic)
    Engine->>DB: INSERT evaluations
    Engine->>DB: INSERT audit_logs
    
    DB-->>Engine: Inserted IDs
    Engine-->>API: Evaluation Results
    API-->>User: JSON Response
```

---

## Models SQLAlchemy

### Model Structure

All models are defined in `src/models/` with the following structure:

```
src/models/
├── __init__.py          # Exports all models, creates tables
├── base.py              # DeclarativeBase, metadata
├── user.py              # User, GitHubAccount
├── repository.py        # Branch
├── control.py           # Control, Rule
├── evidence.py          # Evidence
├── evaluation.py        # Evaluation
└── audit.py             # AuditLog
```

### Core Models

#### 1. User Model

```python
# src/models/user.py
from sqlalchemy import Column, String, DateTime, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(1024), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
```

#### 2. GitHubAccount Model

```python
# src/models/user.py
class GitHubAccount(Base):
    __tablename__ = "github_accounts"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, unique=True)
    github_id = Column(BigInteger, nullable=False, unique=True)
    login = Column(String(255), nullable=False)
    access_token = Column(String(1024), nullable=False)
    refresh_token = Column(String(1024), nullable=False)
    token_expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    user = relationship("User", back_populates="github_account")
```

#### 3. Branch Model

```python
# src/models/repository.py
class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    repository_name = Column(String(255), nullable=False)
    branch_name = Column(String(255), nullable=False)
    last_commit_sha = Column(String(64), nullable=False)
    last_analysis_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("repository_name", "branch_name", name="uq_branch_repo_branch"),
    )
    
    evidences = relationship("Evidence", back_populates="branch")
```

#### 4. Control Model

```python
# src/models/control.py
class Control(Base):
    __tablename__ = "controls"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    rules = relationship("Rule", back_populates="control")
```

#### 5. Rule Model

```python
# src/models/control.py
from sqlalchemy import CheckConstraint

class Rule(Base):
    __tablename__ = "rules"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    control_id = Column(UUID, ForeignKey("controls.id"), nullable=False)
    name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)  # 'EQ', 'AND', 'OR', 'UNKNOWN'
    expression = Column(Text, nullable=False)
    parameters = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("rule_type IN ('EQ', 'AND', 'OR', 'UNKNOWN')", name="chk_rule_type"),
    )
    
    control = relationship("Control", back_populates="rules")
    evaluations = relationship("Evaluation", back_populates="rule")
```

#### 6. Evidence Model

```python
# src/models/evidence.py
class Evidence(Base):
    __tablename__ = "evidences"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    branch_id = Column(UUID, ForeignKey("branches.id"), nullable=False)
    evidence_type = Column(String(100), nullable=False)  # 'file', 'metadata', 'config', 'dependency'
    path = Column(String(1024), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA-256
    raw_content = Column(Text, nullable=True)
    parsed_data = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index("idx_evidence_hash", "content_hash"),
        UniqueConstraint("branch_id", "evidence_type", "path", "content_hash", name="uq_evidence_unique"),
    )
    
    branch = relationship("Branch", back_populates="evidences")
    evaluations = relationship("Evaluation", back_populates="evidence")
```

#### 7. Evaluation Model

```python
# src/models/evaluation.py
from sqlalchemy import Decimal

class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    evidence_id = Column(UUID, ForeignKey("evidences.id"), nullable=False)
    rule_id = Column(UUID, ForeignKey("rules.id"), nullable=False)
    status = Column(String(20), nullable=False)  # 'PASS', 'FAIL', 'UNKNOWN'
    confidence = Column(Decimal(3, 2), nullable=False)  # 0.00 to 1.00
    details = Column(Text, nullable=True)
    evaluated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index("idx_evaluation_evidence_rule", "evidence_id", "rule_id"),
        Index("idx_evaluation_status", "status"),
    )
    
    evidence = relationship("Evidence", back_populates="evaluations")
    rule = relationship("Rule", back_populates="evaluations")
```

#### 8. AuditLog Model

```python
# src/models/audit.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    event_type = Column(String(100), nullable=False)  # 'EVALUATION_STARTED', 'EVALUATION_COMPLETED', etc.
    resource_type = Column(String(50), nullable=False)  # 'EVIDENCE', 'RULE', 'EVALUATION'
    resource_id = Column(UUID, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    metadata = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index("idx_audit_event_time", "event_type", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )
```

### Database Schema Summary

| Table | Primary Key | Unique Constraints | Indexes | Notes |
|-------|-------------|-------------------|---------|-------|
| users | id | email | email | Timestamps with timezone |
| github_accounts | id | user_id, github_id | - | Foreign key to users |
| branches | id | (repository_name, branch_name) | repository_name | For duplicate detection |
| controls | id | name | category | Category for filtering |
| rules | id | - | control_id | Check constraint on rule_type |
| evidences | id | (branch_id, evidence_type, path, content_hash) | content_hash | SHA-256 hash |
| evaluations | id | - | (evidence_id, rule_id), status | Decimal confidence |
| audit_logs | id | - | (event_type, created_at), (resource_type, resource_id) | JSON metadata |

---

## Rule Engine Architecture

### Engine Structure

```
src/engine/
├── __init__.py
├── evaluator.py         # Main RuleEngine class
├── types.py            # RuleType, EvaluationStatus, EvaluationResult
├── operators.py        # EQ, AND, OR operation implementations
└── result.py           # EvaluationResult dataclass
```

### Data Types

#### RuleType Enum

```python
# src/engine/types.py
from enum import Enum

class RuleType(str, Enum):
    EQ = "EQ"      # Equality comparison
    AND = "AND"    # Logical AND
    OR = "OR"      # Logical OR
    UNKNOWN = "UNKNOWN"  # Unknown status
```

#### EvaluationStatus Enum

```python
class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
```

#### EvaluationResult Dataclass

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class EvaluationResult:
    status: EvaluationStatus
    confidence: Decimal  # 0.00 to 1.00
    details: str = ""    # Required for UNKNOWN status
    
    def __post_init__(self):
        # Validate confidence range
        if not (Decimal("0.00") <= self.confidence <= Decimal("1.00")):
            raise ValueError("Confidence must be between 0.00 and 1.00")
        
        # Validate UNKNOWN status
        if self.status == EvaluationStatus.UNKNOWN and not self.details:
            raise ValueError("UNKNOWN status requires details field")
```

### Rule Evaluation Logic

#### 1. EQ Rule (Equality)

```python
# src/engine/operators.py
def evaluate_eq(evidence: Evidence, rule: Rule) -> EvaluationResult:
    """
    Evaluate EQ rule: compare evidence field against expected value.
    
    Rule parameters:
    - field: field name in evidence.parsed_data to compare
    - expected: expected value
    
    Returns PASS if evidence.field == expected, FAIL otherwise.
    """
    field = rule.parameters.get("field")
    expected = rule.parameters.get("expected")
    
    if field is None or expected is None:
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details="Missing required parameters: field or expected"
        )
    
    # Get actual value from evidence
    actual = evidence.parsed_data.get(field) if evidence.parsed_data else None
    
    if actual is None:
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details=f"Field '{field}' not found in evidence"
        )
    
    # Compare values
    passed = actual == expected
    
    return EvaluationResult(
        status=EvaluationStatus.PASS if passed else EvaluationStatus.FAIL,
        confidence=Decimal("1.00") if passed else Decimal("0.00"),
        details=f"Comparison: {actual} == {expected}"
    )
```

#### 2. AND Rule (Logical AND)

```python
def evaluate_and(evidence: Evidence, rule: Rule, sub_evaluators: list) -> EvaluationResult:
    """
    Evaluate AND rule: all conditions must PASS.
    
    Rule parameters:
    - conditions: list of sub-rules to evaluate
    
    Returns PASS only if ALL conditions PASS.
    Confidence = count(PASS) / count(total conditions)
    """
    conditions = rule.parameters.get("conditions", [])
    
    if not conditions:
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details="AND rule has no conditions to evaluate"
        )
    
    pass_count = 0
    details_list = []
    
    for i, condition in enumerate(conditions):
        result = sub_evaluators[i](evidence, condition)
        details_list.append(f"Condition {i+1}: {result.details}")
        
        if result.status == EvaluationStatus.PASS:
            pass_count += 1
    
    total = len(conditions)
    confidence = Decimal(str(pass_count / total))
    
    return EvaluationResult(
        status=EvaluationStatus.PASS if pass_count == total else EvaluationStatus.FAIL,
        confidence=confidence,
        details=f"AND evaluation: {pass_count}/{total} conditions passed. Details: {'; '.join(details_list)}"
    )
```

#### 3. OR Rule (Logical OR)

```python
def evaluate_or(evidence: Evidence, rule: Rule, sub_evaluators: list) -> EvaluationResult:
    """
    Evaluate OR rule: at least one condition must PASS.
    
    Returns PASS if ANY condition PASS.
    Confidence = count(PASS) / count(total conditions)
    """
    conditions = rule.parameters.get("conditions", [])
    
    if not conditions:
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details="OR rule has no conditions to evaluate"
        )
    
    pass_count = 0
    details_list = []
    
    for i, condition in enumerate(conditions):
        result = sub_evaluators[i](evidence, condition)
        details_list.append(f"Condition {i+1}: {result.details}")
        
        if result.status == EvaluationStatus.PASS:
            pass_count += 1
    
    total = len(conditions)
    confidence = Decimal(str(pass_count / total))
    
    return EvaluationResult(
        status=EvaluationStatus.PASS if pass_count >= 1 else EvaluationStatus.FAIL,
        confidence=confidence,
        details=f"OR evaluation: {pass_count}/{total} conditions passed. Details: {'; '.join(details_list)}"
    )
```

#### 4. UNKNOWN Rule

```python
def evaluate_unknown(evidence: Evidence, rule: Rule) -> EvaluationResult:
    """
    Evaluate UNKNOWN rule: returns UNKNOWN with reason from parameters.
    
    Rule parameters:
    - reason: explanation for UNKNOWN status
    
    Confidence is always 0.00 for UNKNOWN.
    """
    reason = rule.parameters.get("reason", "Unknown reason provided")
    
    return EvaluationResult(
        status=EvaluationStatus.UNKNOWN,
        confidence=Decimal("0.00"),
        details=reason
    )
```

### Main RuleEngine Class

```python
# src/engine/evaluator.py
from typing import Callable, Dict
from decimal import Decimal

class RuleEngine:
    """
    Deterministic rule evaluation engine.
    
    Properties:
    - 100% reproducible: same inputs → same outputs
    - No side effects: no datetime.now(), random(), I/O
    - All timestamps provided as parameters
    """
    
    # Operation dispatch table
    OPERATIONS: Dict[str, Callable] = {
        "EQ": evaluate_eq,
        "AND": evaluate_and,
        "OR": evaluate_or,
        "UNKNOWN": evaluate_unknown,
    }
    
    def __init__(self):
        """Initialize the rule engine."""
        self._cache: Dict[tuple, EvaluationResult] = {}  # (evidence_id, rule_id) → result
    
    def evaluate(
        self,
        evidence: Evidence,
        rule: Rule,
        evaluated_at: datetime,  # Timestamp from outside, not computed
        cache_results: bool = True
    ) -> EvaluationResult:
        """
        Evaluate a rule against evidence.
        
        Args:
            evidence: The evidence to evaluate
            rule: The rule to apply
            evaluated_at: Timestamp (from outside, not datetime.now())
            cache_results: Whether to cache results for reproducibility
            
        Returns:
            EvaluationResult with status, confidence, and details
            
        Raises:
            ValueError: If rule_type is unknown
        """
        # Check cache first (for determinism verification)
        cache_key = (str(evidence.id), str(rule.id))
        if cache_results and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get operation function
        operation = self.OPERATIONS.get(rule.rule_type)
        if operation is None:
            raise ValueError(f"Unknown rule type: {rule.rule_type}")
        
        # Evaluate
        result = operation(evidence, rule)
        
        # Cache result
        if cache_results:
            self._cache[cache_key] = result
        
        return result
    
    def evaluate_multiple(
        self,
        evidence: Evidence,
        rules: list,
        evaluated_at: datetime
    ) -> list:
        """
        Evaluate multiple rules against evidence.
        
        Returns list of (rule, result) tuples.
        """
        return [
            (rule, self.evaluate(evidence, rule, evaluated_at))
            for rule in rules
        ]
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system - essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Rule evaluation produces valid results

*For any* valid evidence and rule, the RuleEngine SHALL produce an EvaluationResult with a valid status (PASS, FAIL, or UNKNOWN), confidence between 0.00 and 1.00, and details field present for UNKNOWN status.

**Validates: Requirements 10.1, 10.6, 12.3, 12.4**

### Property 2: EQ rule comparison is correct

*For any* evidence with a field and an EQ rule specifying that field and expected value, the rule SHALL return PASS if the actual field value equals the expected value, and FAIL otherwise.

**Validates: Requirements 10.2, 27.1**

### Property 3: AND rule requires all conditions to pass

*For any* AND rule with N conditions, the rule SHALL return PASS if and only if ALL N conditions return PASS. The confidence SHALL equal N/N = 1.00 in this case.

**Validates: Requirements 10.3, 27.2**

### Property 4: OR rule requires at least one condition to pass

*For any* OR rule with N conditions, the rule SHALL return PASS if at least ONE condition returns PASS. The confidence SHALL equal pass_count/N.

**Validates: Requirements 10.4, 27.3**

### Property 5: Determinism - same inputs produce same outputs

*For any* evidence and rule, if the RuleEngine evaluates them 100 times with the same inputs, ALL 100 results SHALL be identical.

**Validates: Requirements 11.4, 11.5, 17.1, 17.2, 17.3, 18.3, 35.1**

### Property 6: UNKNOWN status has zero confidence

*For any* evaluation result with status UNKNOWN, the confidence field SHALL be exactly 0.00.

**Validates: Requirements 12.4, 16.4, 27.4**

### Property 7: Confidence calculation is accurate

*For any* rule evaluation, the confidence field SHALL equal the ratio of PASS conditions to total conditions. For EQ rules (single condition), confidence is 1.00 for PASS and 0.00 for FAIL.

**Validates: Requirements 10.5, 27.5**

### Property 8: Deterministic engines produce identical results across instances

*For any* evidence and rule evaluated by two separate RuleEngine instances, the results SHALL be identical.

**Validates: Requirements 35.1**

### Property 9: Evidence persistence preserves data integrity

*For any* evidence inserted into the database, the record can be retrieved by its UUID and all fields (including content_hash) SHALL be identical to the original.

**Validates: Requirements 28.3**

### Property 10: Evidence uniqueness by hash prevents duplicates

*For any* evidence with a specific (branch_id, evidence_type, path, content_hash) combination, attempting to insert another evidence with the same combination SHALL result in only one record existing in the database.

**Validates: Requirements 28.2**

### Property 11: Evaluation persistence enables round-trip retrieval

*For any* evaluation created by the RuleEngine, the evaluation can be retrieved from the database by its ID with all fields intact.

**Validates: Requirements 28.3**

### Property 12: Audit logging captures all evaluation completions

*For any* evaluation created, an audit_log entry with event_type EVALUATION_COMPLETED SHALL be created with the evaluation_id in metadata.

**Validates: Requirements 29.2**

---

## Error Handling

### Error Types

```python
# src/engine/errors.py
class RuleEngineError(Exception):
    """Base exception for rule engine errors."""
    pass

class ValidationError(RuleEngineError):
    """Raised when validation fails."""
    pass

class EvaluationError(RuleEngineError):
    """Raised when evaluation fails."""
    pass

class DatabaseConnectionError(RuleEngineError):
    """Raised when database connection fails."""
    pass

class MissingParameterError(ValidationError):
    """Raised when required parameter is missing."""
    pass

class UnknownRuleTypeError(EvaluationError):
    """Raised when rule type is unknown."""
    pass
```

### Error Handling in RuleEngine

```python
def evaluate(self, evidence: Evidence, rule: Rule, ...) -> EvaluationResult:
    """Evaluate with error handling."""
    try:
        # Validation
        if rule.rule_type not in self.OPERATIONS:
            raise UnknownRuleTypeError(f"Unknown rule type: {rule.rule_type}")
        
        # Evaluation
        result = self.OPERATIONS[rule.rule_type](evidence, rule)
        
        return result
        
    except MissingParameterError as e:
        # Convert to UNKNOWN result
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details=f"Missing parameter: {str(e)}"
        )
    except Exception as e:
        # Log error and return UNKNOWN
        self._log_error(e, evidence, rule)
        return EvaluationResult(
            status=EvaluationStatus.UNKNOWN,
            confidence=Decimal("0.00"),
            details=f"Evaluation failed: {str(e)}"
        )
```

### Error Logging to Audit

```python
def _log_error(self, error: Exception, evidence: Evidence, rule: Rule):
    """Log error to audit_log."""
    audit_entry = AuditLog(
        event_type="ERROR",
        resource_type="EVALUATION",
        resource_id=evidence.id,
        metadata={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "evidence_id": str(evidence.id),
            "rule_id": str(rule.id),
            "rule_type": rule.rule_type
        }
    )
    self.session.add(audit_entry)
    self.session.commit()
```

---

## Testing Strategy

### Dual Testing Approach

- **Unit tests**: Verify specific examples, edge cases, error conditions
- **Property tests**: Verify universal properties across all inputs
- **Integration tests**: Verify database persistence and full flows

### Property-Based Tests (Using fast-check)

```python
# tests/test_rule_engine_properties.py
import pytest
from decimal import Decimal
from fast_check import given, strings, integers, booleans
from src.engine.types import RuleType, EvaluationStatus, EvaluationResult
from src.engine.evaluator import RuleEngine

@pytest.fixture
def engine():
    return RuleEngine()

# Property 1: Valid results
@given(rule_type=strings().filter(lambda s: s in ["EQ", "AND", "OR", "UNKNOWN"]))
def test_property_1_valid_results(engine, rule_type):
    """Property 1: Rule evaluation produces valid results."""
    # Generate random evidence and rule
    evidence = generate_random_evidence()
    rule = generate_random_rule(rule_type)
    
    result = engine.evaluate(evidence, rule, datetime.now())
    
    assert result.status in [EvaluationStatus.PASS, EvaluationStatus.FAIL, EvaluationStatus.UNKNOWN]
    assert Decimal("0.00") <= result.confidence <= Decimal("1.00")
    if result.status == EvaluationStatus.UNKNOWN:
        assert len(result.details) > 0
```

### Test Configuration

```python
# pytest.ini
[pytest]
addopts = -v --cov=src --cov-report=term-missing --cov-fail-under=85
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    property: property-based tests
    integration: integration tests
```

### Test Categories

#### Unit Tests (Specific Examples)
- EQ rule with exact values
- AND rule with mixed PASS/FAIL
- OR rule with single PASS
- UNKNOWN rule with reason

#### Property-Based Tests (Universal Properties)
- Property 1: Valid results across all rule types
- Property 2: EQ comparison correctness
- Property 3: AND all-or-nothing behavior
- Property 4: OR at-least-one behavior
- Property 5: Determinism (100 iterations)
- Property 6: UNKNOWN confidence is 0.00
- Property 7: Confidence accuracy
- Property 8: Cross-instance determinism

#### Integration Tests
- Evidence insert and retrieve
- Evaluation create and retrieve
- Audit log creation
- Duplicate evidence rejection

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install flake8 pytest pytest-cov
      - name: Run flake8
        run: flake8 src/ tests/ --max-line-length=120

  unit-tests:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
      - name: Run unit tests with coverage
        run: |
          pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=85

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pytest psycopg2-binary
      - name: Run integration tests
        run: |
          DATABASE_URL=postgresql://test:test@localhost:5432/test pytest tests/integration/
```

---

## Directory Structure

```
src/
├── models/               # SQLAlchemy models
│   ├── __init__.py       # Exports, create_all()
│   ├── base.py           # DeclarativeBase
│   ├── user.py           # User, GitHubAccount
│   ├── repository.py     # Branch
│   ├── control.py        # Control, Rule
│   ├── evidence.py       # Evidence
│   ├── evaluation.py     # Evaluation
│   └── audit.py          # AuditLog
│
├── engine/               # Rule engine
│   ├── __init__.py
│   ├── evaluator.py      # RuleEngine class
│   ├── types.py          # Enums, dataclasses
│   ├── operators.py      # EQ, AND, OR, UNKNOWN
│   └── result.py         # EvaluationResult
│
├── adapters/             # Database adapters
│   ├── __init__.py
│   ├── database.py       # Session, engine
│   ├── evidence_repo.py  # Evidence CRUD
│   ├── evaluation_repo.py # Evaluation CRUD
│   └── audit_repo.py     # Audit logging
│
├── api/                  # REST API endpoints
│   ├── __init__.py
│   ├── auth.py           # GitHub OAuth
│   ├── evaluations.py    # Evaluation endpoints
│   └── schemas.py        # Pydantic schemas
│
└── config/               # Configuration
    ├── __init__.py
    ├── settings.py       # Environment-based config
    └── database.py       # DB connection

tests/
├── __init__.py
├── conftest.py           # Fixtures
├── test_engine/          # Engine tests
│   ├── __init__.py
│   ├── test_properties.py   # Property tests
│   ├── test_unit.py         # Unit tests
│   └── test_determinism.py  # Determinism tests
├── test_integration/     # Integration tests
│   ├── __init__.py
│   ├── test_database.py     # DB persistence
│   ├── test_evidence.py     # Evidence flow
│   └── test_audit.py        # Audit logging
└── fixtures/             # Test data
    ├── __init__.py
    ├── evidences.py
    ├── rules.py
    └── evaluations.py
```

---

## Design Decisions and Justification

### 1. Deterministic Rule Engine

**Decision**: No `datetime.now()`, `random()`, or external calls in rule evaluation.

**Justification**: 
- **Reproducibility**: Same inputs → same outputs, critical for debugging
- **Testability**: Property-based testing requires deterministic behavior
- **Audit trail**: Evaluations timestamped by caller, not engine
- **35.1**: Scalability requires identical results across instances

**Implementation**: Timestamps (`evaluated_at`) passed as parameters from calling code.

### 2. INSERT-Only Persistence

**Decision**: Critical tables (evidence, evaluation, audit_log) never UPDATE or DELETE.

**Justification**:
- **Audit trail**: Complete history of all evaluations
- **Compliance**: Regulatory requirements for immutable logs
- **35.3**: State stored in PostgreSQL, not memory
- **Simplicity**: No conflict resolution for concurrent updates

**Implementation**: Database constraints + application-level enforcement.

### 3. Property-Based Testing for Core Logic

**Decision**: Use PBT for rule evaluation, determinism, and round-trip persistence.

**Justification**:
- **Requirements 10-12**: Rule evaluation logic has universal properties
- **Requirements 17-19**: Determinism is a perfect PBT target
- **Requirements 28**: Database round-trips can be property-tested
- **100 iterations**: Finds edge cases that example tests miss

**Not suitable for PBT**:
- **Requirements 1**: OAuth flow - specific sequence, not universal property
- **Requirements 2-9**: Schema definitions - configuration, not behavior
- **Requirements 13-14**: Constraints - schema checks, not runtime properties
- **Requirements 20-25**: CI/CD - workflow configuration, not code logic

### 4. Separation of Concerns

**Decision**: Clear modules for models, engine, adapters, API.

**Justification**:
- **Testability**: Engine can be tested with mocks
- **Maintainability**: Clear boundaries for changes
- **30.1**: Clean architecture for maintainability
- **30.4**: Dependency injection between layers

### 5. Result Caching for Determinism Verification

**Decision**: RuleEngine caches results by (evidence_id, rule_id).

**Justification**:
- **35.4**: Cache reused results for efficiency
- **Determinism verification**: Same inputs always return cached result
- **Performance**: Avoid recomputing identical evaluations

### 6. Decimal for Confidence

**Decision**: Use `Decimal(3, 2)` for confidence field.

**Justification**:
- **Precision**: Exact decimal arithmetic, no floating-point errors
- **Range**: 0.00 to 1.00 with 2 decimal places
- **Database**: PostgreSQL supports Decimal with precision/scale

### 7. JSONB for Parameters and Metadata

**Decision**: Use JSONB for rule parameters and audit metadata.

**Justification**:
- **Flexibility**: Different rules need different parameters
- **Queryability**: PostgreSQL can query JSONB fields
- **Extensibility**: Add new fields without schema migration

### 8. Composite Unique Constraints

**Decision**: Use composite constraints (e.g., evidence uniqueness by hash).

**Justification**:
- **Data integrity**: Database enforces uniqueness
- **Duplicate detection**: Automatic, no application logic needed
- **35.2**: Connection pooling for high volume

### 9. Indexing Strategy

**Decision**: Strategic indexes on:
- `content_hash` for duplicate detection
- `(evidence_id, rule_id)` for evaluation lookups
- `(event_type, created_at)` for audit queries

**Justification**:
- **35.4**: Performance optimization
- **Common queries**: Fast lookups for typical operations
- **34.1**: Meet performance targets

### 10. Error Handling Returns UNKNOWN

**Decision**: Rule evaluation errors return UNKNOWN with details, not exceptions.

**Justification**:
- **33.2**: Graceful degradation for evaluation failures
- **33.1**: Database errors use exceptions, rule errors use UNKNOWN
- **Robustness**: System continues despite partial failures

---

## CI/CD Pipeline Design

### Pipeline Stages

```mermaid
graph LR
    A[Push/Pull Request] --> B[Lint Job]
    B -->|Success| C[Unit Tests Job]
    C -->|Success| D[Integration Tests Job]
    D -->|Success| E[Merge to Main]
    
    B -->|Failure| F[Fail Fast]
    C -->|Failure| F
    D -->|Failure| F
    
    style F fill:#ff6b6b
    style E fill:#51cf66
```

### Lint Job

**Purpose**: Code style and quality checks

**Steps**:
1. Checkout code
2. Install flake8
3. Run `flake8 src/ tests/ --max-line-length=120`
4. Output specific violations if any
5. Exit code 1 on failures, 0 on success

**Failure Feedback**:
```
❌ Linting failed: 5 violations found
src/engine/operators.py:45:1: E302 expected 2 blank lines, found 1
src/engine/operators.py:52:80: E501 line too long (125 > 120 characters)
```

### Unit Tests Job

**Purpose**: Verify rule engine logic with 85%+ coverage

**Steps**:
1. Checkout code
2. Install pytest and pytest-cov
3. Run `pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=85`
4. Generate coverage report
5. Fail if coverage < 85%

**Coverage Requirements**:
- **Rule engine code**: >85% coverage
- **Test types**: Property tests + unit tests + determinism tests
- **Coverage report**: Term-missing shows lines missing coverage

**Failure Feedback**:
```
❌ Coverage failure: 82% coverage (85% required)
Missing coverage in:
  src/engine/operators.py:45-50 (AND rule confidence calculation)
  src/engine/evaluator.py:120-125 (Error handling path)
```

### Integration Tests Job

**Purpose**: Verify database persistence and full flows

**Steps**:
1. Checkout code
2. Start PostgreSQL service
3. Install psycopg2-binary
4. Run integration tests
5. Verify evidence and evaluation persistence

**Test Cases**:
1. Evidence insert and retrieve by hash
2. Evaluation create and retrieve by ID
3. Audit log creation for evaluations
4. Duplicate evidence rejection

**Failure Feedback**:
```
❌ Integration test failed: Evidence uniqueness constraint violated
Expected: Duplicate evidence with same hash rejected
Actual: Duplicate record created with different UUID
```

### Success Criteria

- **Lint**: 0 violations
- **Unit tests**: 100% pass, >85% coverage
- **Integration tests**: 100% pass
- **Overall**: All jobs pass → PR can merge

### Failure Handling

- **Fail fast**: Lint fails → no tests run
- **Sequential**: Unit tests only run if lint passes
- **Clear messages**: Specific errors with line numbers and failure details
- **Log links**: Full logs available for debugging

---

## Conclusion

This design provides a complete blueprint for implementing the SecureCode Core Domain:

- ✅ **Deterministic rule engine** with property-based testing
- ✅ **8 SQLAlchemy models** with proper constraints and indexes
- ✅ **INSERT-only persistence** for audit trail
- ✅ **Comprehensive testing strategy** (unit + property + integration)
- ✅ **CI/CD pipeline** with linting, unit tests, integration tests
- ✅ **Clear directory structure** for maintainability

The design is concreto, verificable, and ready for implementation. Each component is designed for testability and determinism, meeting all requirements 1-35.
