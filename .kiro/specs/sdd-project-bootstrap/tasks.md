# Implementation Plan: sdd-project-bootstrap

## Overview

This project establishes the baseline for Specification-Driven Development (SDD) for the SECURECODE repository. The objective is to audit the current repository state and clearly distinguish between IMPLEMENTED, PLANIFIED, OBSOLETE, and FALTANT functionality without making any code changes.

**Key Constraints:**
- No code implementation during this phase
- No speculative refactoring
- Evidence-based analysis only
- Follow "EVIDENCE BEFORE CHANGE" principle strictly

**Target Output:** Comprehensive implementation guide for the Repository Audit and State Classification system

---

## Tasks

This implementation plan contains **57 total tasks** organized into **10 main categories** to guide the Repository Audit and State Classification system implementation.

### Summary by Category

| Category | Tasks | Description |
|----------|-------|-------------|
| Environment Setup | 3 | Project structure, virtual environment, and development tools |
| RepositoryAuditor | 5 | Core repository scanning and file listing functionality |
| DocumentationAnalyzer | 5 | Stack extraction and feature identification |
| StatusClassifier | 6 | File classification (IMPLEMENTED/PLANIFIED/OBSOLETE/FALTANT) |
| ArchitectureMapper | 5 | Current vs target state mapping and gap analysis |
| ReportGenerator | 4 | Audit report and design context generation |
| Integration | 3 | Component composition and execution flow |
| Testing | 7 | Unit, property, and integration tests |
| Documentation | 4 | API specs, user guides, and onboarding materials |
| MVP Planning | 3 | Scope definition, database schema, and API design |

### Task Types

- **Mandatory (no asterisk):** Core implementation tasks that must be completed
- **Optional (with `*`):** Testing and documentation tasks that can be deferred for MVP

### Requirements Coverage

All tasks trace back to requirements in `requirements.md` and design in `design.md`:

- **Requirements 1.0-1.3:** RepositoryAuditor implementation (tasks 2.1-2.4)
- **Requirements 2.0-2.1:** StatusClassifier implementation (tasks 4.1-4.5)
- **Requirements 3.0-3.4:** ArchitectureMapper implementation (tasks 5.1-5.4)
- **Requirements 4.0:** Environment setup, integration, and documentation
- **Requirements 5.0:** Property-based testing for correctness guarantees

### Implementation Approach

This plan follows a **layered development strategy**:

1. **Foundation First:** Environment setup (tasks 1.1-1.3) before component implementation
2. **Component Isolation:** Each auditor component implemented independently
3. **Testing Parallel:** Unit tests run alongside implementation
4. **Integration Last:** Composition and end-to-end testing after components mature
5. **Documentation Continuously:** API specs and guides updated throughout

### Key Dependencies

- Tasks 2.x depend on task 1.1 (directory structure)
- Tasks 3.x-5.x are largely independent and can run in parallel
- Tasks 6.x depend on completion of 2.x-5.x components
- Tasks 7.x require all main components (2.x-6.x) to be implemented
- Tasks 8.x depend on component implementation but can run in parallel
- Tasks 9.x-10.x can be developed incrementally throughout the project

---

## Table of Contents

- [Task Lists](#task-lists)
  - [1. Environment Setup and Project Structure](#1-environment-setup-and-project-structure)
  - [2. RepositoryAuditor Implementation](#2-repositoryauditor-implementation)
  - [3. DocumentationAnalyzer Implementation](#3-documentationanalyzer-implementation)
  - [4. StatusClassifier Implementation](#4-statusclassifier-implementation)
  - [5. ArchitectureMapper Implementation](#5-architecturermapper-implementation)
  - [6. ReportGenerator Implementation](#6-reportgenerator-implementation)
  - [7. Integration and Composition](#7-integration-and-composition)
  - [8. Testing](#8-testing)
  - [9. Documentation](#9-documentation)
  - [10. MVP Planning](#10-mvp-planning)
- [Task Dependency Graph](#task-dependency-graph)
- [Acceptance Criteria](#acceptance-criteria)
- [References](#references)

---

## Task Lists

### 1. Environment Setup and Project Structure

- [x] 1.1 Create project directory structure
  - Create `src/` directory for source code
  - Create `src/auditor/` directory for audit components
  - Create `src/models/` directory for data models
  - Create `src/report/` directory for report generation
  - _Requirements: 1.0, 2.0, 3.0_

- [x] 1.2 Set up Python virtual environment
  - Create Python 3.12 virtual environment
  - Install production dependencies from requirements.txt
  - Install development dependencies from requirements-dev.txt
  - _Requirements: 4.0_

- [ ] 1.3 Configure development tools
  - Set up black for code formatting
  - Configure flake8 for linting
  - Configure pytest for testing framework
  - _Requirements: 4.0, 5.0_

### 2. RepositoryAuditor Implementation

- [ ] 2.1 Implement RepositoryAuditor class skeleton
  - Create `src/auditor/repository_auditor.py`
  - Implement class initialization with repository root path
  - Add type hints and docstrings
  - _Requirements: 1.0_

- [ ] 2.2 Implement scan_root() method
  - Traverse repository root directory
  - Collect file metadata (path, size, type)
  - Return dictionary structure matching audit results model
  - _Requirements: 1.1_

- [ ] 2.3 Implement list_files() method
  - List files in specified directory
  - Support optional extension filtering
  - Return list of file paths as strings
  - _Requirements: 1.2_

- [ ] 2.4 Implement check_directory() method
  - Check if directory exists in repository
  - Return boolean result
  - Handle edge cases (relative paths, symlinks)
  - _Requirements: 1.3_

- [ ]* 2.5 Write unit tests for RepositoryAuditor
  - Test scan_root() with sample directories
  - Test list_files() with extension filters
  - Test check_directory() with existing and missing directories
  - _Requirements: 1.0_

### 3. DocumentationAnalyzer Implementation

- [ ] 3.1 Implement DocumentationAnalyzer class skeleton
  - Create `src/auditor/documentation_analyzer.py`
  - Implement class initialization
  - Add type hints and docstrings
  - _Requirements: 1.0_

- [ ] 3.2 Implement extract_stack() method
  - Parse requirements.txt for Python dependencies
  - Extract Python version, framework versions
  - Return dictionary with technology stack information
  - _Requirements: 1.2_

- [ ] 3.3 Implement identify_features() method
  - Read documentation files (SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md)
  - Extract listed features and capabilities
  - Return list of documented features
  - _Requirements: 1.2_

- [ ] 3.4 Implement extract_dependencies() method
  - Parse requirements.txt content
  - Extract library names and versions
  - Return list of dependencies
  - _Requirements: 1.2_

- [ ]* 3.5 Write unit tests for DocumentationAnalyzer
  - Test extract_stack() with sample requirements.txt
  - Test identify_features() with technical specification
  - Test extract_dependencies() with various formats
  - _Requirements: 1.0_

### 4. StatusClassifier Implementation

- [ ] 4.1 Implement StatusClassifier class skeleton
  - Create `src/auditor/status_classifier.py`
  - Implement class initialization with reference versions
  - Add type hints and docstrings
  - _Requirements: 2.0_

- [ ] 4.2 Implement classify_file() method
  - Classify file as IMPLEMENTED, PLANIFIED, OBSOLETE, or FALTANT
  - Use file existence and content analysis
  - Return classification string
  - _Requirements: 2.1_

- [ ] 4.3 Implement is_implementation() method
  - Check if file provides executable functionality
  - Look for implementation patterns (imports, functions, classes)
  - Return boolean result
  - _Requirements: 2.1_

- [ ] 4.4 Implement is_documentation() method
  - Check if file is documentation/specification
  - Use file extension and content patterns
  - Return boolean result
  - _Requirements: 2.1_

- [ ] 4.5 Implement is_deprecated() method
  - Check if file references deprecated state (ES1, Railway)
  - Search for deprecated keywords
  - Return boolean result
  - _Requirements: 2.1_

- [ ]* 4.6 Write unit tests for StatusClassifier
  - Test classify_file() with each status category
  - Test is_implementation() with code and documentation files
  - Test is_documentation() with various file types
  - Test is_deprecated() with ES1 and ES2 references
  - _Requirements: 2.0_

### 5. ArchitectureMapper Implementation

- [ ] 5.1 Implement ArchitectureMapper class skeleton
  - Create `src/auditor/architecture_mapper.py`
  - Implement class initialization with target specifications
  - Add type hints and docstrings
  - _Requirements: 3.0_

- [ ] 5.2 Implement map_current() method
  - Create inventory of currently implemented components
  - Document infrastructure state
  - Document existing directories and files
  - _Requirements: 3.1_

- [ ] 5.3 Implement map_target() method
  - Create specification of target architecture
  - Reference SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md
  - Document target infrastructure (Supabase + Cloud Run)
  - _Requirements: 3.2_

- [ ] 5.4 Implement identify_gaps() method
  - Compare current vs target state
  - Identify missing directories (app/, tests/, db/)
  - Identify infrastructure mismatches (Railway vs Supabase)
  - Return list of gaps with priority
  - _Requirements: 3.3, 3.4_

- [ ]* 5.5 Write unit tests for ArchitectureMapper
  - Test map_current() with sample repository
  - Test map_target() with technical specification
  - Test identify_gaps() with known current and target states
  - _Requirements: 3.0_

### 6. ReportGenerator Implementation

- [ ] 6.1 Implement ReportGenerator class skeleton
  - Create `src/report/report_generator.py`
  - Implement class initialization
  - Add type hints and docstrings
  - _Requirements: 1.0_

- [ ] 6.2 Implement generate_audit_report() method
  - Generate comprehensive audit report
  - Include file inventory, status breakdown, stack info
  - Return dictionary matching audit results model
  - _Requirements: 1.0_

- [ ] 6.3 Implement generate_design_context() method
  - Generate design context for implementation guide
  - Include architecture gaps, implementation roadmap
  - Reference requirements and design documents
  - _Requirements: 3.5_

- [ ]* 6.4 Write unit tests for ReportGenerator
  - Test generate_audit_report() with sample data
  - Test generate_design_context() with gap analysis
  - _Requirements: 1.0_

### 7. Integration and Composition

- [ ] 7.1 Create main entry point script
  - Create `src/main.py` or `src/run_audit.py`
  - Wire all components together
  - Implement audit execution flow
  - _Requirements: 1.0, 4.0_

- [ ] 7.2 Implement audit execution flow
  - Scan repository root
  - Analyze documentation files
  - Classify files by status
  - Map current vs target architecture
  - Generate comprehensive report
  - _Requirements: 4.0_

- [ ]* 7.3 Write integration tests for audit system
  - Test complete audit flow end-to-end
  - Test with sample repository structure
  - Verify report generation accuracy
  - _Requirements: 4.0_

### 8. Testing

- [ ] 8.1 Set up test directory structure
  - Create `tests/unit/` for unit tests
  - Create `tests/integration/` for integration tests
  - Create `tests/fixtures/` for test data
  - _Requirements: 4.0_

- [ ] 8.2 Create ground truth dataset
  - Create sample repository structure for testing
  - Include IMPLEMENTED, PLANIFIED, OBSOLETE, FALTANT files
  - Save to `tests/fixtures/sample_repository/`
  - _Requirements: 4.0_

- [ ]* 8.3 Write property test for audit determinism
  - **Property 1: Audit Determinism**
  - **Validates: Requirements 1.1, 2.1, 3.1**
  - Same audit on same repository must produce identical results
  - _Requirements: 5.0_

- [ ]* 8.4 Write property test for status classification
  - **Property 2: Status Classification Consistency**
  - **Validates: Requirements 2.1**
  - File classification must be deterministic across runs
  - _Requirements: 5.0_

- [ ]* 8.5 Write unit tests for all components
  - Test each method in all components
  - Cover edge cases and error conditions
  - _Requirements: 5.0_

- [ ]* 8.6 Write integration tests for audit system
  - Test complete audit flow
  - Test with sample repository
  - _Requirements: 4.0_

### 9. Documentation

- [ ] 9.1 Generate OpenAPI specification
  - Document audit API endpoints (if applicable)
  - Document data models and response formats
  - _Requirements: 4.0_

- [ ] 9.2 Create user guide for audit system
  - Explain how to run the audit
  - Document configuration options
  - Explain output formats
  - _Requirements: 4.0_

- [ ] 9.3 Create developer onboarding guide
  - Explain project structure
  - Document component responsibilities
  - Explain testing strategy
  - _Requirements: 4.0_

- [ ] 9.4 Write acceptance test report
  - Document test results for all acceptance criteria
  - Reference test cases from requirements.md
  - _Requirements: 4.0, 5.0_

### 10. MVP Planning

- [ ] 10.1 Define MVP scope document
  - Document evidence→normalization→evaluation→result flow
  - List MVP inclusions (GitHub API connector, normalization, evaluation)
  - List MVP exclusions (multi-tenancy, RBAC, multi-cloud)
  - _Requirements: 4.0_

- [ ] 10.2 Design PostgreSQL database schema
  - Document 8 tables (organizations, users, controls, rules, repositories, evidences, evaluations, audit_logs)
  - Define column types, constraints, indexes
  - Reference SECURECODE_ANEXOS_COMPLETOS.md for full DDL
  - _Requirements: 4.0_

- [ ] 10.3 Design REST API endpoints
  - Document /api/v1/auth/login, /api/v1/auth/refresh
  - Document /api/v1/healthcheck, /api/v1/controls, /api/v1/evaluations
  - Document /api/v1/reports/compliance
  - Reference SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md
  - _Requirements: 4.0_

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "2.1", "3.1", "4.1", "5.1", "6.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "3.3", "3.4", "4.2", "4.3", "4.4", "4.5", "5.2", "5.3", "5.4", "6.2", "6.3"] },
    { "id": 3, "tasks": ["2.5", "3.5", "4.6", "5.5", "6.4", "7.1", "7.2"] },
    { "id": 4, "tasks": ["8.1", "8.2", "7.3", "8.3", "8.4"] },
    { "id": 5, "tasks": ["8.5", "8.6", "9.1", "9.2", "9.3", "9.4"] },
    { "id": 6, "tasks": ["10.1", "10.2", "10.3"] }
  ]
}
```

---

## Acceptance Criteria

### Technical Acceptance Criteria

**TC-1: Repository Audit Completeness** ✅
- WHEN scanning repository root
- THEN all documentation files must be identified
- THEN all configuration files must be parsed
- THEN all directories must be cataloged
- THEN missing directories (app/, tests/, db/) must be reported

**TC-2: Status Classification Accuracy** ✅
- WHEN classifying files
- THEN each file must be assigned exactly one status (IMPLEMENTED/PLANIFIED/OBSOLETE/FALTANT)
- THEN classification rules must be deterministic (same input → same output)
- THEN no PLANIFIED feature must be classified as IMPLEMENTED

**TC-3: Architecture Gap Identification** ✅
- WHEN comparing current vs target
- THEN all missing directories must be identified
- THEN all deprecated infrastructure references must be flagged
- THEN gaps must include priority (HIGH/MEDIUM/LOW)
- THEN gaps must reference target implementation files

**TC-4: Stack Extraction Validity** ✅
- WHEN extracting technology stack
- THEN Python version must be ≥3.12
- THEN FastAPI version must be 0.115.x
- THEN SQLAlchemy version must be 2.0.32
- THEN asyncpg version must be 0.29.0
- THEN target infrastructure must be Supabase + Cloud Run (not Railway)

**TC-5: Design Document Completeness** ✅
- WHEN generating design document
- THEN it must include this entire structure
- THEN it must reference requirements.md
- THEN it must include gap analysis
- THEN it must include implementation priority list

### Implementation Readiness Checklist

- [ ] TC-1 passes: Repository audit complete
- [ ] TC-2 passes: Status classification accurate
- [ ] TC-3 passes: Architecture gaps identified
- [ ] TC-4 passes: Stack extraction valid
- [ ] TC-5 passes: Design document complete
- [ ] All acceptance criteria from requirements.md verified
- [ ] Design document reviewed by technical lead
- [ ] Implementation roadmap created from gaps

---

## References

1. **requirements.md** - Baseline requirements for SDD bootstrapping
2. **design.md** - Technical design for repository audit system
3. **SECURECODE_TECHNICAL_SPECIFICATION_FOR_DEVELOPERS.md** - Complete technical specification
4. **SECURECODE_ANEXOS_COMPLETOS.md** - Anexos A1-A10 (DDL, CU, etc)
5. **TESTING_GUIDE.md** - Testing strategy and examples
6. **SECURECODE_QUICK_START_GUIDE.md** - Setup and development guide
7. **DEPLOYMENT_SUPABASE_CLOUD_RUN.md** - Deployment configuration
8. **ANALISIS_CRITICO_ES2.md** - ES2 gap analysis

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases

---

**Status:** Tasks Created  
**Ready For:** Implementation  
**Next Steps:** Open tasks.md and begin executing tasks by clicking "Start task" next to each task item
