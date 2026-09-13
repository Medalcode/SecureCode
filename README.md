# SecureCode

A GRC (Governance, Risk, Compliance) platform for automated security control evaluation.

## Overview

SecureCode is being developed using Specification-Driven Development (SDD).

## Current Status

### Project Bootstrap (sdd-project-bootstrap)

**Status:** ? Specification Complete, Ready for Implementation

This project establishes the baseline for SDD by auditing the current repository state and classifying functionality into four categories:

- **IMPLEMENTED**: Files that exist and provide executable functionality
- **PLANIFIED**: Files that describe future implementation (docs, specs)
- **OBSOLETE**: Files that describe deprecated state
- **FALTANT**: Files or directories that should exist but are missing

**Spec Files:
- [requirements.md](.kiro/specs/sdd-project-bootstrap/requirements.md) - 5 core requirements
- [design.md](.kiro/specs/sdd-project-bootstrap/design.md) - Technical architecture (5 auditor components)
- [tasks.md](.kiro/specs/sdd-project-bootstrap/tasks.md) - 57 implementation tasks

**Key Components:
1. RepositoryAuditor - Scans repository structure
2. DocumentationAnalyzer - Extracts technology stack
3. StatusClassifier - Categorizes files by implementation status
4. ArchitectureMapper - Maps current vs target architecture
5. ReportGenerator - Generates audit reports

## Development

Follow the Specification-Driven Development protocol:

1. **AUDIT** - Inspect repository, identify current state
2. **EVIDENCE** - Classify findings (IMPLEMENTED/PLANIFIED/OBSOLETE/FALTANT)
3. **DECISION** - Explicitly state what problem will be solved
4. **SPECIFICATION** - Create requirements.md, design.md, tasks.md
5. **MINIMAL IMPLEMENTATION** - Implement according to specification
6. **VALIDATION** - Run tests, verify acceptance criteria
7. **STOP** - Stop after validation, don't add unrelated improvements

See [.kiro/specs/](.kiro/specs/) for active and completed specs.
