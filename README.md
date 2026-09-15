# SecureCode

A GRC (Governance, Risk, Compliance) platform for automated security control evaluation.

## Overview

SecureCode is being developed using Specification-Driven Development (SDD).

## Current Status

### Project Bootstrap - REMOVED

The sdd-project-bootstrap specification has been removed. It was a repository-auditing feature,
not part of the SecureCode product MVP.

**SDD Bootstrap** should describe *how* we develop the product, not be a product feature itself.

### Core Domain - REMOVED

The core-domain-securecode specification has been removed. It was over-scoped, including:
- GitHub OAuth
- User authentication/authorization
- PostgreSQL persistence
- REST API
- Cloud deployment
- CI/CD pipeline
- Multi-tenancy

These are FUTURE capabilities, not the first implementation slice.

## Development

Follow the Specification-Driven Development protocol:

1. **AUDIT** - Inspect repository, identify current state
2. **EVIDENCE** - Classify findings (IMPLEMENTED/PLANIFIED/OBSOLETE/FALTANT)
3. **DECISION** - Explicitly state what problem will be solved
4. **SPECIFICATION** - Create requirements.md, design.md, tasks.md
5. **MINIMAL IMPLEMENTATION** - Implement according to specification
6. **VALIDATION** - Run tests, verify acceptance criteria
7. **STOP** - Stop after validation, don't add unrelated improvements

## Product Vision

SecureCode evaluates security controls against observable evidence.

Core Domain:

Control -> Rule -> Evidence -> Evaluation -> PASS/FAIL/UNKNOWN

First Vertical Slice (planned):

GitHub Evidence -> Normalization -> Deterministic Evaluation -> PASS/FAIL/UNKNOWN

This will be implemented as a minimal specification focused solely on:
- Deterministic rule engine
- GH-001 Branch Protection Required control
- Unit tests with property-based testing
- No OAuth, no persistence, no API, no infrastructure

See docs/specs/ for active specifications.

## Ground Truth

SecureCode uses a Ground Truth dataset to empirically validate the accuracy of the rule engine against real-world data.
- **GH-001** utilizes controlled synthetic repositories (`Medalcode/securecode-ground-truth`) to guarantee immutability and reproducibility.
- The dataset is versioned inside the repository (`data/ground_truth/`).
- **Evidence:** Real API responses from the synthetic repositories are captured and stored in `docs/evidence/ground_truth/` to serve as an irrefutable baseline. The 6 scenarios for GH-001 have been empirically validated and their raw JSON responses are saved as evidence.

## SDD Structure

SecureCode/
+-- docs/
    +-- specs/          # Active specifications
    +-- hooks/          # SDD workflow hooks
+-- src/                # Application source code (when implemented)
+-- tests/              # Test suite (when implemented)
+-- README.md           # This file

