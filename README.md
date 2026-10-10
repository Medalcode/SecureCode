# SecureCode

A GRC (Governance, Risk, Compliance) platform for automated security control evaluation.

## Overview

SecureCode is being developed using Specification-Driven Development (SDD).

## Current Status

### Implemented Capabilities
- **GH-001 (Branch Protection Required)**: Deterministic evaluation engine with peer approval & stale dismissal thresholds.
- **GH-002 (Default Branch Protection Enabled)**: Deterministic evaluation engine for primary branch protection status.
- **GitHub REST API Adapters**: Live evidence extraction and normalization with graceful degradation on unobservable states.
- **PostgreSQL Persistence**: Immutable, traceable evaluation records with canonical JSONB hashes, foreign key relations, and Alembic migrations.
- **FastAPI HTTP Boundaries**: Fully typed endpoints (`/api/v1/evaluations/gh-001`, `/api/v1/evaluations/gh-002`, `/health`).
- **User Authentication & Traceability**: Argon2id password hashing, HS256 JWT access tokens, dependency-injected user authorization, and `requested_by_user_id` audit linkages.
- **CI/CD**: GitHub Actions remote validation workflows covering API, SQLite integration, and containerized PostgreSQL.

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

First Vertical Slice (Implemented):

GitHub Evidence -> Normalization -> Deterministic Evaluation -> Traceable DB Record -> HTTP Response

See `docs/specs/` for active specifications.

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
        +-- api/        # FastAPI REST endpoints
        +-- adapters/   # External infrastructure (GitHub/Postgres)
+-- tests/              # Test suite (Unit/Integration)
+-- scripts/            # Traceability, Validation, Artifact extraction
+-- pyproject.toml      # Package configuration
+-- README.md           # This file
