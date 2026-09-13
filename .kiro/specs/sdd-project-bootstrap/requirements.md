# Requirements Document

## Introduction

This document establishes the baseline requirements for bootstrapping Specification-Driven Development (SDD) for the SECURECODE project. The objective is to audit the current repository state and clearly distinguish between IMPLEMENTED, PLANIFIED (documented but not implemented), OBSOLETE, and FALTANT (missing) functionality.

**Key Principle: EVIDENCE BEFORE CHANGE**
- No functionality shall be implemented during this phase
- No speculative refactoring shall be performed
- No documented feature shall be assumed as implemented without code evidence
- All requirements must be verifiable through code or file existence

**Current State (as of audit):**
- Repository contains 22+ documentation files (~1.3 MB total)
- Python 3.12 stack with FastAPI, SQLAlchemy, PostgreSQL configured
- Makefile, docker-compose.yml, and setup.sh for development
- No actual implementation code (app/, tests/, db/ directories absent)
- ES2 documentation supersedes ES1 (Railway → Supabase + Cloud Run infrastructure)

## Glossary

- **SecureCode**: The main project name - a GRC (Governance, Risk, Compliance) platform for automated security control evaluation
- **SDD (Specification-Driven Development)**: Methodology where specification drives implementation, not the reverse
- **MVP (Minimum Viable Product)**: The smallest functional implementation demonstrating the evidence→normalization→evaluation→result flow
- **Evidence**: Data collected from external sources (GitHub API, AWS services, internal systems) that will be evaluated against security rules
- **Normalization**: Process of transforming external data into canonical JSON format with SHA-256 hash for integrity verification
- **Deterministic Evaluation**: Property that the same evidence + rule always produces the same PASS, FAIL, or UNKNOWN result
- **PASS**: Evidence satisfies the rule criteria
- **FAIL**: Evidence demonstrates rule violation
- **UNKNOWN**: Insufficient evidence available (not an error state)
- **EVIDENCE BEFORE CHANGE**: Core principle requiring evidence of existing state before any modification

## Requirements

### Requirement 1: Audit Current Repository State

**User Story:** As a developer setting up SDD for SecureCode, I want to audit the current repository state, so that I can establish a clear baseline of what exists and what needs to be implemented.

#### Acceptance Criteria

1. WHEN the repository root is inspected, THE Auditor SHALL identify all documentation files present
2. WHEN documentation files are analyzed, THE Auditor SHALL extract the project stack (Python 3.12, FastAPI, SQLAlchemy, PostgreSQL)
3. WHEN implementation directories are checked, THE Auditor SHALL determine that app/, tests/, db/ directories are MISSING
4. WHERE evidence of infrastructure is requested, THE Auditor SHALL identify Railway as OBSOLETE and Supabase + Cloud Run as TARGET
5. WHEN setup scripts are examined, THE Auditor SHALL identify Makefile, docker-compose.yml, and setup.sh as IMPLEMENTED configuration

### Requirement 2: Distinguish Implementation Status Categories

**User Story:** As a project maintainer, I want to clearly distinguish between IMPLEMENTED, PLANIFIED, OBSOLETE, and FALTANT functionality, so that the team can focus on bootstrapping gaps without confusion.

#### Acceptance Criteria

1. WHEN examining the repository, THE Status_Categorizer SHALL classify files into exactly one category:
   - IMPLEMENTED: Files that exist and provide executable functionality (Makefile, docker-compose.yml, setup.sh)
   - PLANIFIED: Files that exist but describe future implementation (SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md, SECURECODE_ANEXOS_COMPLETOS.md)
   - OBSOLETE: Files that describe deprecated state (ES1 documentation, Railway references)
   - FALTANT: Files or directories that should exist but are missing (app/, tests/, db/, ground_truth_dataset.csv)
2. WHILE categorizing, THE Status_Categorizer SHALL NOT assume PLANIFIED features are IMPLEMENTED
3. WHERE documentation references features, THE Status_Categorizer SHALL NOT treat those references as evidence of implementation
4. IF a file exists but contains only TODO comments, THE Status_Categorizer SHALL classify it as FALTANT

### Requirement 3: Document Current vs Target Architecture

**User Story:** As a technical lead, I want to document the current implementation state versus the target architecture, so that implementation priorities are clear and no assumptions are made about existing code.

#### Acceptance Criteria

1. THE Architectural_Documenter SHALL create a current state inventory listing all implemented components
2. THE Architectural_Documenter SHALL create a target state specification based on SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md
3. WHERE infrastructure is described, THE Architectural_Documenter SHALL clearly distinguish:
   - Current: Railway (deprecated, $5-10/month)
   - Target: Supabase + Cloud Run (free tier, $0/month)
4. WHEN comparing current vs target, THE Architectural_Documenter SHALL explicitly list missing components:
   - No app/ directory structure
   - No domain/engine/ evaluator implementation
   - No adapters/ implementation (GitHub, PostgreSQL)
   - No tests/ directory with test files
   - No database migrations (Alembic)
5. FOR multi-tenancy considerations, THE Architectural_Documenter SHALL note that organizations/users tables exist in schema but not in implementation

### Requirement 4: Define MVP Scope and Execution Flow

**User Story:** As a product owner, I want to define the MVP scope and the evidence→normalization→evaluation→result flow, so that implementation efforts are focused on the minimum viable product.

#### Acceptance Criteria

1. WHEN MVP scope is requested, THE Scope_Definer SHALL include:
   - 1 GitHub API connector (read-only)
   - Canonical JSON normalization with SHA-256 hashing
   - Deterministic rule evaluation engine
   - PostgreSQL persistence for immutable results
   - REST API with admin user authentication
   - Table reports and JSON export
2. WHEN MVP scope is requested, THE Scope_Definer SHALL exclude:
   - Multi-tenancy
   - RBAC granular permissions
   - AWS/Azure/GCP connectors
   - Automatic remediation
   - AI in decision core
3. WHEN the execution flow is described, THE Flow_Definer SHALL specify:
   - STEP 1: Obtain evidence from external source (GitHub API)
   - STEP 2: Normalize evidence to canonical JSON format
   - STEP 3: Evaluate canonical evidence against rule using deterministic engine
   - STEP 4: Return PASS/FAIL/UNKNOWN (UNKNOWN is NOT automatically FAIL)
   - STEP 5: Persist evaluation result in immutable database table
4. WHERE normalization is specified, THE Normalizer SHALL apply SHA-256 hash to canonical JSON for integrity verification

### Requirement 5: Ensure Deterministic Evaluation with UNKNOWN as Valid State

**User Story:** As a quality assurance engineer, I want to ensure that evaluation results are deterministic and that UNKNOWN is treated as a valid state distinct from FAIL, so that results are reproducible and interpretable.

#### Acceptance Criteria

1. WHILE evaluation is performed, THE Evaluator SHALL produce the same result for identical inputs (rule + evidence)
2. WHERE evidence is complete and satisfies rule, THE Evaluator SHALL return PASS
3. WHERE evidence is complete but violates rule, THE Evaluator SHALL return FAIL
4. WHERE evidence is insufficient, missing, or unavailable, THE Evaluator SHALL return UNKNOWN (NOT FAIL)
5. IF the same evaluation is re-run 10 times, THE Evaluator SHALL produce identical results (reproducibility)
6. FOR UNKNOWN results, THE System SHALL NOT treat them as failures - UNKNOWN shall be tracked separately in statistics

## Unknown State Handling

**Explicit Requirement:** UNKNOWN is a valid evaluation state that indicates insufficient evidence. It is NOT an error condition and MUST NOT be automatically converted to FAIL.

**Testing Guidance:**
- UNKNOWN count shall be tracked separately from FAIL count
- Compliance percentage shall be calculated as: PASS / (PASS + FAIL) × 100 (UNKNOWN excluded from denominator)
- Confidence percentage shall be calculated as: (PASS + FAIL) / Total × 100 (shows proportion of decidable cases)

## References

1. SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md (66 KB)
2. SECURECODE_QUICK_START_GUIDE.md (8 KB)
3. DEPLOYMENT_SUPABASE_CLOUD_RUN.md (18 KB)
4. SECURECODE_ANEXOS_COMPLETOS.md (33 KB)
5. TESTING_GUIDE.md (45 KB)
6. ANALISIS_CRITICO_ES2.md (22 KB)
