# Implementation Plan: SecureCode Core Domain

## Overview

This plan implements the SecureCode Core Domain MVP - a GRC platform for automated security control evaluation. The implementation covers:

- **8 SQLAlchemy models** for PostgreSQL persistence (INSERT-ONLY)
- **Deterministic rule engine** (100% reproducible, no side effects)
- **Property-based testing** for critical logic with 85%+ coverage
- **CI/CD pipeline** with GitHub Actions (lint → unit → integration)

**Difficulty Key:**
- 🔵 Low: Simple code implementation
- 🟡 Medium: Moderate complexity, some design decisions
- 🔴 High: Complex logic, multiple components, integration

---

## Tasks

### Phase 1: Project Setup and Configuration

- [ ] 1.1 Create project directory structure
  - [ ] Create `src/models/`, `src/engine/`, `src/adapters/`, `src/api/`, `src/config/`, `tests/`
  - [ ] Create `src/models/__init__.py` (exports, create_all())
  - [ ] Create `src/engine/__init__.py` (exports RuleEngine, types)
  - [ ] Create `src/adapters/__init__.py` (exports database session)
  - [ ] Create `src/api/__init__.py` (exports API endpoints)
  - [ ] Create `src/config/__init__.py` (exports settings)
  - [ ] Create `tests/__init__.py`, `tests/conftest.py` (fixtures)
  - **Difficulty**: 🔵 Low
  - **Estimate**: 15 min
  - **Requirements**: 30

- [ ] 1.2 Configure Alembic for database migrations
  - [ ] Install `alembic` and `sqlalchemy`
  - [ ] Run `alembic init migrations`
  - [ ] Configure `alembic.ini` with database URL template
  - [ ] Create `migrations/env.py` with environment-based config
  - [ ] Create `migrations/alembic.yml` with versioning strategy
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 32

- [ ] 1.3 Configure docker-compose for development
  - [ ] Create `docker-compose.yml` with PostgreSQL service
  - [ ] Configure environment variables for development
  - [ ] Create `docker-compose.override.yml` for local development
  - [ ] Add health checks for PostgreSQL service
  - [ ] Create `scripts/dev-setup.sh` for easy setup
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 32

---

### Phase 2: SQLAlchemy Models (8 Tables)

- [ ] 2.1 Implement `src/models/base.py`
  - [ ] Create `DeclarativeBase` class
  - [ ] Configure metadata with naming conventions
  - [ ] Add `create_all()` function for schema creation
  - **Difficulty**: 🔵 Low
  - **Estimate**: 10 min
  - **Requirements**: 26

- [ ] 2.2 Implement `src/models/user.py` (User, GitHubAccount)
  - [ ] Implement `User` model with columns: id, email, name, avatar_url, created_at, updated_at
  - [ ] Implement `GitHubAccount` model with columns: id, user_id, github_id, login, tokens, expires_at
  - [ ] Add foreign key relationship: GitHubAccount → User
  - [ ] Add back_populates relationship: User → github_account
  - [ ] Add index on User.email for fast lookup
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 2, 3

- [ ] 2.3 Implement `src/models/repository.py` (Branch)
  - [ ] Implement `Branch` model with columns: id, repository_name, branch_name, last_commit_sha, last_analysis_at, created_at
  - [ ] Add unique constraint: (repository_name, branch_name)
  - [ ] Add index on repository_name for filtering
  - [ ] Add relationship to evidences
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 15 min
  - **Requirements**: 4

- [ ] 2.4 Implement `src/models/control.py` (Control, Rule)
  - [ ] Implement `Control` model with columns: id, name, description, category, enabled, created_at
  - [ ] Implement `Rule` model with columns: id, control_id, name, rule_type, expression, parameters, created_at
  - [ ] Add check constraint on rule_type: EQ, AND, OR, UNKNOWN
  - [ ] Add relationships: Control → rules, Rule → control, Rule → evaluations
  - [ ] Add index on Control.category for filtering
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 5, 6

- [ ] 2.5 Implement `src/models/evidence.py` (Evidence)
  - [ ] Implement `Evidence` model with columns: id, branch_id, evidence_type, path, content_hash, raw_content, parsed_data, created_at
  - [ ] Add SHA-256 hash computation for content_hash
  - [ ] Add index on content_hash for duplicate detection
  - [ ] Add unique constraint: (branch_id, evidence_type, path, content_hash)
  - [ ] Add relationship to evaluations
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 7

- [ ] 2.6 Implement `src/models/evaluation.py` (Evaluation)
  - [ ] Implement `Evaluation` model with columns: id, evidence_id, rule_id, status, confidence, details, evaluated_at, created_at
  - [ ] Use `Decimal(3, 2)` for confidence field (0.00-1.00)
  - [ ] Add indexes on (evidence_id, rule_id) and status
  - [ ] Add relationships: Evaluation → evidence, Evaluation → rule
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 15 min
  - **Requirements**: 8

- [ ] 2.7 Implement `src/models/audit.py` (AuditLog)
  - [ ] Implement `AuditLog` model with columns: id, event_type, resource_type, resource_id, user_id, metadata, created_at
  - [ ] Add indexes on (event_type, created_at) and (resource_type, resource_id)
  - [ ] Add relationship to users (optional)
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 15 min
  - **Requirements**: 9

- [ ] 2.8 Update `src/models/__init__.py`
  - [ ] Export all models
  - [ ] Implement `create_all_tables()` function
  - [ ] Add type hints for all exports
  - **Difficulty**: 🔵 Low
  - **Estimate**: 10 min
  - **Requirements**: 26

---

### Phase 3: Rule Engine Implementation

- [ ] 3.1 Implement `src/engine/types.py`
  - [ ] Create `RuleType` enum: EQ, AND, OR, UNKNOWN
  - [ ] Create `EvaluationStatus` enum: PASS, FAIL, UNKNOWN
  - [ ] Import `Decimal` from decimal module
  - **Difficulty**: 🔵 Low
  - **Estimate**: 10 min
  - **Requirements**: 27

- [ ] 3.2 Implement `src/engine/result.py` (EvaluationResult)
  - [ ] Create `EvaluationResult` dataclass with fields: status, confidence, details
  - [ ] Implement `__post_init__()` validation:
    - Confidence range 0.00-1.00
    - UNKNOWN requires details field
  - [ ] Make dataclass frozen for immutability
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 15 min
  - **Requirements**: 10

- [ ] 3.3 Implement `src/engine/operators.py` (EQ, AND, OR, UNKNOWN)
  - [ ] Implement `evaluate_eq(evidence, rule)` - EQ rule evaluation
    - Extract field and expected from parameters
    - Compare evidence.parsed_data[field] == expected
    - Return PASS/FAIL with confidence 1.00/0.00
  - [ ] Implement `evaluate_and(evidence, rule, sub_evaluators)` - AND rule evaluation
    - Evaluate all conditions
    - Return PASS only if ALL conditions PASS
    - Confidence = pass_count / total_count
  - [ ] Implement `evaluate_or(evidence, rule, sub_evaluators)` - OR rule evaluation
    - Evaluate all conditions
    - Return PASS if AT LEAST ONE PASS
    - Confidence = pass_count / total_count
  - [ ] Implement `evaluate_unknown(evidence, rule)` - UNKNOWN rule evaluation
    - Extract reason from parameters
    - Return UNKNOWN with confidence 0.00 and reason in details
  - **Difficulty**: 🔴 High
  - **Estimate**: 60 min
  - **Requirements**: 10, 11, 12, 27

- [ ] 3.4 Implement `src/engine/evaluator.py` (RuleEngine)
  - [ ] Create `RuleEngine` class with `OPERATIONS` dispatch table
  - [ ] Implement `__init__()` with cache dictionary
  - [ ] Implement `evaluate(evidence, rule, evaluated_at, cache_results=True)`
    - Check cache first for determinism
    - Get operation from dispatch table
    - Call operation function
    - Cache result if enabled
    - Return EvaluationResult
  - [ ] Implement `evaluate_multiple(evidence, rules, evaluated_at)`
    - Return list of (rule, result) tuples
  - [ ] Add validation for unknown rule types
  - [ ] Add error handling to return UNKNOWN with details
  - **Difficulty**: 🔴 High
  - **Estimate**: 45 min
  - **Requirements**: 10, 11, 12, 27, 30

---

### Phase 4: Persistence Layer

- [ ] 4.1 Implement `src/adapters/database.py`
  - [ ] Create SQLAlchemy engine with connection pooling
  - [ ] Implement `get_session()` factory function
  - [ ] Load DATABASE_URL from environment variables
  - [ ] Add error handling for missing DATABASE_URL
  - [ ] Add engine configuration for PostgreSQL
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 14, 32

- [ ] 4.2 Implement evidence repository (`src/adapters/evidence_repo.py`)
  - [ ] Implement `save_evidence(session, evidence)` - INSERT ONLY
  - [ ] Implement `find_by_hash(session, content_hash)` - duplicate detection
  - [ ] Implement `find_by_branch(session, branch_id)` - filter by branch
  - [ ] Implement `find_by_unique(session, branch_id, evidence_type, path, hash)` - unique constraint check
  - [ ] All methods use INSERT ONLY (no UPDATE/DELETE)
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 13, 28

- [ ] 4.3 Implement evaluation repository (`src/adapters/evaluation_repo.py`)
  - [ ] Implement `save_evaluation(session, evaluation)` - INSERT ONLY
  - [ ] Implement `find_by_evidence_rule(session, evidence_id, rule_id)` - lookup
  - [ ] Implement `find_by_status(session, status)` - filter by PASS/FAIL/UNKNOWN
  - [ ] Implement `find_by_branch(session, branch_id)` - join evaluations with evidence
  - [ ] All methods use INSERT ONLY
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 13, 28

- [ ] 4.4 Implement audit repository (`src/adapters/audit_repo.py`)
  - [ ] Implement `log_event(session, event_type, resource_type, resource_id, user_id, metadata)`
  - [ ] Implement `find_by_event_type(session, event_type, start_time, end_time)`
  - [ ] Implement `find_by_resource(session, resource_type, resource_id)`
  - [ ] All methods use INSERT ONLY
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 25 min
  - **Requirements**: 13, 29

- [ ] 4.5 Implement `src/adapters/__init__.py`
  - [ ] Export database session factory
  - [ ] Export all repositories
  - [ ] Add type hints for all exports
  - **Difficulty**: 🔵 Low
  - **Estimate**: 10 min
  - **Requirements**: 30

---

### Phase 5: Integration and Main Application

- [ ] 5.1 Implement `src/config/settings.py`
  - [ ] Create `Settings` class with environment-based configuration
  - [ ] Load DATABASE_URL, enable OAuth flags, etc.
  - [ ] Add validation for required environment variables
  - [ ] Create `get_settings()` factory function
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 32

- [ ] 5.2 Implement `src/main.py`
  - [ ] Create main application entry point
  - [ ] Initialize database engine and session
  - [ ] Create RuleEngine instance
  - [ ] Add command-line interface for evaluation
  - [ ] Add basic error handling and logging
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 25 min
  - **Requirements**: 30, 33

- [ ] 5.3 Implement API layer (`src/api/evaluations.py`)
  - [ ] Create API endpoints for evaluation management
  - [ ] Implement POST /evaluations for new evaluations
  - [ ] Implement GET /evaluations/:id for retrieval
  - [ ] Implement GET /evaluations?branch_id=X for filtering
  - [ ] Add Pydantic schemas for request/response validation
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 40 min
  - **Requirements**: 30

- [ ] 5.4 Implement main.py integration
  - [ ] Wire RuleEngine with repositories
  - [ ] Implement evaluation flow: retrieve evidence → evaluate → save → log audit
  - [ ] Add transaction handling with session.commit()
  - [ ] Implement audit logging on evaluation completion
  - **Difficulty**: 🔴 High
  - **Estimate**: 30 min
  - **Requirements**: 29

---

### Phase 6: Testing Strategy

#### Unit Tests

- [ ] 6.1 Write `tests/test_engine/test_operators.py`
  - [ ] Test `evaluate_eq()` with PASS case (exact match)
  - [ ] Test `evaluate_eq()` with FAIL case (mismatch)
  - [ ] Test `evaluate_eq()` with UNKNOWN case (missing field)
  - [ ] Test `evaluate_and()` with all PASS (confidence = 1.00)
  - [ ] Test `evaluate_and()` with mixed PASS/FAIL
  - [ ] Test `evaluate_and()` with all FAIL (confidence = 0.00)
  - [ ] Test `evaluate_or()` with at least one PASS
  - [ ] Test `evaluate_or()` with all FAIL (confidence = 0.00)
  - [ ] Test `evaluate_unknown()` with reason
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 45 min
  - **Requirements**: 16, 18, 19

- [ ] 6.2 Write `tests/test_engine/test_result.py`
  - [ ] Test EvaluationResult with valid PASS
  - [ ] Test EvaluationResult with valid FAIL
  - [ ] Test EvaluationResult with valid UNKNOWN
  - [ ] Test confidence validation (out of range)
  - [ ] Test UNKNOWN requires details
  - **Difficulty**: 🔵 Low
  - **Estimate**: 20 min
  - **Requirements**: 16

#### Determinism Tests

- [ ] 6.3 Write `tests/test_engine/test_determinism.py`
  - [ ] Test 10 evaluations with same inputs produce identical results
  - [ ] Test 100 evaluations with same inputs produce identical results
  - [ ] Test multiple RuleEngine instances produce same results
  - [ ] Test no random() calls in rule engine code
  - [ ] Test no datetime.now() calls in rule engine code
  - **Difficulty**: 🔴 High
  - **Estimate**: 30 min
  - **Requirements**: 11, 17, 18, 19, 35

#### Property-Based Tests (PBT)

- [ ] 6.4 Write `tests/test_engine/test_properties.py`
  - [ ] Property 1: Valid results across all rule types
    - Generate random evidence and rules
    - Verify status in [PASS, FAIL, UNKNOWN]
    - Verify confidence in [0.00, 1.00]
    - Verify UNKNOWN has details
  - [ ] Property 2: EQ rule comparison correctness
    - Generate random evidence with field values
    - Generate EQ rules with expected values
    - Verify PASS if equal, FAIL if not
  - [ ] Property 3: AND rule all-or-nothing behavior
    - Generate AND rules with N conditions
    - Verify PASS only if ALL conditions PASS
    - Verify confidence = N/N = 1.00
  - [ ] Property 4: OR rule at-least-one behavior
    - Generate OR rules with N conditions
    - Verify PASS if ANY condition PASS
    - Verify confidence = pass_count/N
  - [ ] Property 5: Determinism across 100 iterations
    - Evaluate same evidence/rule 100 times
    - Verify all results identical
  - [ ] Property 6: UNKNOWN has zero confidence
    - Generate UNKNOWN rules
    - Verify confidence = 0.00
  - [ ] Property 7: Confidence accuracy
    - Generate rules with known PASS/FAIL counts
    - Verify confidence = pass_count/total_count
  - [ ] Property 8: Cross-instance determinism
    - Create two RuleEngine instances
    - Evaluate same inputs on both
    - Verify identical results
  - **Difficulty**: 🔴 High
  - **Estimate**: 90 min
  - **Requirements**: 15, 17, 18, 19

#### Integration Tests

- [ ] 6.5 Write `tests/test_integration/test_database.py`
  - [ ] Test evidence insert and retrieve by UUID
  - [ ] Test evidence uniqueness by hash (duplicate rejection)
  - [ ] Test evaluation insert and retrieve by ID
  - [ ] Test audit_log creation for evaluations
  - [ ] Test database connection and session handling
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 40 min
  - **Requirements**: 14, 28, 29

- [ ] 6.6 Write `tests/test_integration/test_evidence_flow.py`
  - [ ] Test end-to-end evidence storage flow
  - [ ] Test evidence retrieval by branch
  - [ ] Test evidence hash duplicate detection
  - [ ] Test evidence with NULL raw_content
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 7, 28

- [ ] 6.7 Write `tests/test_integration/test_evaluation_flow.py`
  - [ ] Test rule evaluation and persistence
  - [ ] Test multiple rules against same evidence
  - [ ] Test evaluation retrieval with joins
  - [ ] Test audit_log creation after evaluation
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 8, 29

---

### Phase 7: CI/CD Pipeline

- [ ] 7.1 Create `.flake8` configuration file
  - [ ] Set max-line-length = 120
  - [ ] Configure ignore rules for project-specific needs
  - [ ] Add exclude patterns for migrations, venv
  - **Difficulty**: 🔵 Low
  - **Estimate**: 10 min
  - **Requirements**: 22

- [ ] 7.2 Create GitHub Actions workflow (`.github/workflows/ci.yml`)
  - [ ] Configure lint job:
    - Run flake8 on src/ and tests/
    - Fail on violations
    - Output specific error messages
  - [ ] Configure unit-tests job (depends: lint):
    - Run pytest with coverage
    - Require >85% coverage
    - Generate coverage report
  - [ ] Configure integration-tests job (depends: unit-tests):
    - Start PostgreSQL service
    - Run integration tests
    - Verify database persistence
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 30 min
  - **Requirements**: 20, 21, 22, 23, 24

- [ ] 7.3 Create `.github/workflows/cd.yml` for deployments
  - [ ] Configure staging deployment on develop push
  - [ ] Configure production deployment on main push
  - [ ] Add manual approval for production
  - **Difficulty**: 🟡 Medium
  - **Estimate**: 20 min
  - **Requirements**: 35

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.3"]
    },
    {
      "id": 1,
      "tasks": ["1.2", "2.1", "3.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "2.4", "3.2"]
    },
    {
      "id": 3,
      "tasks": ["2.5", "2.6", "2.7", "3.3"]
    },
    {
      "id": 4,
      "tasks": ["2.8", "3.4", "4.1"]
    },
    {
      "id": 5,
      "tasks": ["4.2", "4.3", "4.4", "4.5"]
    },
    {
      "id": 6,
      "tasks": ["5.1", "5.2", "6.1", "6.2"]
    },
    {
      "id": 7,
      "tasks": ["5.3", "5.4", "6.3", "6.4"]
    },
    {
      "id": 8,
      "tasks": ["6.5", "6.6", "6.7", "7.1"]
    },
    {
      "id": 9,
      "tasks": ["7.2", "7.3"]
    }
  ]
}
```

---

## Notes

### Task Categories by Difficulty

| Difficulty | Tasks | Estimation |
|------------|-------|------------|
| 🔵 Low | 1.1, 1.3, 2.1, 2.8, 3.1, 3.2, 4.5, 5.1, 7.1 | ~2 hours |
| 🟡 Medium | 1.2, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 4.1, 4.2, 4.3, 4.4, 5.2, 5.3, 6.1, 6.2, 6.5, 6.6, 6.7, 7.2 | ~6 hours |
| 🔴 High | 3.3, 3.4, 5.4, 6.3, 6.4 | ~4 hours |

**Total Estimated Time**: ~12 hours

### Testing Coverage

- **Unit Tests**: Operator functions, result validation
- **Determinism Tests**: 100 iterations to verify reproducibility
- **Property-Based Tests**: All correctness properties from design
- **Integration Tests**: Database persistence, end-to-end flows

**Coverage Target**: >85% for rule engine code

### CI/CD Pipeline

```
push → [lint] → [unit-tests] → [integration-tests] → merge
```

- **Lint**: flake8 with max-line-length=120
- **Unit Tests**: pytest with pytest-cov, require >85%
- **Integration Tests**: PostgreSQL service, persistence verification

### Requirements Traceability

| Task | Requirements |
|------|-------------|
| 1.1 | 30 |
| 1.2 | 32 |
| 1.3 | 32 |
| 2.1 | 26 |
| 2.2 | 2, 3 |
| 2.3 | 4 |
| 2.4 | 5, 6 |
| 2.5 | 7 |
| 2.6 | 8 |
| 2.7 | 9 |
| 2.8 | 26 |
| 3.1 | 27 |
| 3.2 | 10 |
| 3.3 | 10, 11, 12, 27 |
| 3.4 | 10, 11, 12, 27, 30 |
| 4.1 | 14, 32 |
| 4.2 | 13, 28 |
| 4.3 | 13, 28 |
| 4.4 | 13, 29 |
| 4.5 | 30 |
| 5.1 | 32 |
| 5.2 | 30, 33 |
| 5.3 | 30 |
| 5.4 | 29 |
| 6.1 | 16, 18, 19 |
| 6.2 | 16 |
| 6.3 | 11, 17, 18, 19, 35 |
| 6.4 | 15, 17, 18, 19 |
| 6.5 | 14, 28, 29 |
| 6.6 | 7, 28 |
| 6.7 | 8, 29 |
| 7.1 | 22 |
| 7.2 | 20, 21, 22, 23, 24 |
| 7.3 | 35 |

### Property-Based Testing

The following properties from the design document are implemented as PBT:

1. **Property 1**: Valid results across all rule types
2. **Property 2**: EQ rule comparison correctness
3. **Property 3**: AND rule all-or-nothing behavior
4. **Property 4**: OR rule at-least-one behavior
5. **Property 5**: Determinism (100 iterations)
6. **Property 6**: UNKNOWN has zero confidence
7. **Property 7**: Confidence accuracy
8. **Property 8**: Cross-instance determinism

### INSERT-Only Enforcement

All persistence operations use INSERT only:
- Evidence records: New UUID for changes
- Evaluation records: Never updated
- AuditLog records: Never updated or deleted
- Application-level enforcement in repository methods

---

## Workflow Completion

This task list is ready for implementation. Each task can be executed by:

1. Opening the `tasks.md` file
2. Clicking "Start task" next to any task item
3. Following the incremental steps to complete the feature

The tasks are ordered to build on each other logically:
- First set up the project structure and models
- Then implement the rule engine logic
- Add persistence layer
- Create integration points
- Write comprehensive tests
- Set up CI/CD pipeline
