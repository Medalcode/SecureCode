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

## Validation & Benchmarking

The deterministic accuracy of the SecureCode engine is empirically validated against synthetic scenarios.

The reference dataset, raw evidence, and benchmark metrics are maintained externally in the [securecode-ground-truth](https://github.com/Medalcode/securecode-ground-truth) repository.

## SDD Structure

SecureCode/
+-- docs/
    +-- specs/          # Active specifications
    +-- hooks/          # SDD workflow hooks
+-- src/
    +-- securecode/
        +-- engine/     # Deterministic evaluation engine
        +-- models/     # Evidence models
+-- tests/              # Test suite
+-- pyproject.toml      # Package configuration
+-- README.md           # This file
