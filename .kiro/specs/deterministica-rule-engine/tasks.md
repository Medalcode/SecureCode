# Implementation Plan: Deterministic Rule Engine

## Overview

This implementation plan creates the first vertical slice of SecureCode: a deterministic rule engine for evaluating security controls. The system processes evidence (e.g., GitHub branch protection settings) and determines whether controls PASS, FAIL, or remain UNKNOWN based on deterministic rules.

## Tasks

- [ ] 1. Establish project structure and domain interfaces
  - Create directory structure under src/
  - Define core TypeScript interfaces for Evidence, Rule, and Evaluation
  - Set up testing framework (Jest + fast-check)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 2. Implement evidence representation
  - [ ] 2.1 Create RawEvidence and NormalizedEvidence interfaces
    - Define TypeScript interfaces per design
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.2 Write property test for evidence preservation
    - **Property 1: Evidence Preservation**
    - **Validates: Requirements 1.5**

  - [ ] 2.3 Implement GitHubBranchProtectionEvidence model
    - Create concrete implementation for GH-001 evidence
    - _Requirements: 1.1, 2.1_

- [ ] 3. Implement rule representation
  - [ ] 3.1 Create Rule and RuleCriteria interfaces
    - Define TypeScript interfaces per design
    - _Requirements: 2.1, 2.2_

  - [ ] 3.2 Implement GH-001 rule instance
    - Create GH-001 rule with required_review_approvals >= 2 AND dismiss_stale_reviews == true
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 3.3 Write property test for rule serialization
    - **Property: Rule round-trip serialization**
    - **Validates: Requirements 7.2**

- [ ] 4. Implement deterministic evaluator
  - [ ] 4.1 Create Evaluator class with PASS/FAIL/UNKNOWN return types
    - Implement evaluation logic per design
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 4.2 Implement evaluation result structure
    - Create Evaluation class with result, rule_id, evidence_id, reason
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 4.3 Write property test for evaluation determinism
    - **Property 2: Evaluation Determinism**
    - **Validates: Requirements 3.5, 6.5**

  - [ ]* 4.4 Write property test for pass semantics
    - **Property 3: Pass Semantics**
    - **Validates: Requirements 4.1**

  - [ ]* 4.5 Write property test for fail semantics
    - **Property 4: Fail Semantics**
    - **Validates: Requirements 4.2**

  - [ ]* 4.6 Write property test for unknown semantics
    - **Property 5: Unknown Semantics**
    - **Validates: Requirements 4.3**

  - [ ]* 4.7 Write property test for pass/fail exclusivity
    - **Property 6: Pass/Fail Mutual Exclusivity**
    - **Validates: Requirements 4.5**

- [ ] 5. Implement GH-001 evaluation
  - [ ] 5.1 Create GH-001 evaluator function
    - Check required_review_approvals >= 2
    - Check dismiss_stale_reviews == true
    - _Requirements: 2.5, 4.1, 4.2, 4.3_

  - [ ] 5.2 Implement evaluation pipeline
    - Evidence Normalizer → Rule_Evaluator → Result
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 5.3 Write property test for reproducibility
    - **Property 7: Evaluation Reproducibility**
    - **Validates: Requirements 8.5**

  - [ ]* 5.4 Write property test for rule application consistency
    - **Property 8: Rule Application Consistency**
    - **Validates: Requirements 6.4**

- [ ] 6. Implement error handling
  - [ ] 6.1 Create EvidenceNormalizer with validation
    - Reject invalid evidence with clear error messages
    - Preserve original data on rejection
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 6.2 Implement rule-evidence mismatch handling
    - Return UNKNOWN when rule cannot be applied
    - Provide clear reason field
    - _Requirements: 7.2_

  - [ ]* 6.3 Write property test for invalid evidence handling
    - **Property: Invalid evidence rejection**
    - **Validates: Requirements 7.1**

  - [ ]* 6.4 Write property test for rule-evidence mismatch
    - **Property: Rule-evidence mismatch handling**
    - **Validates: Requirements 7.2**

- [ ] 7. Integration testing
  - [ ] 7.1 Write end-to-end pipeline test
    - Raw evidence → Normalized evidence → Evaluation result
    - Verify determinism across multiple runs
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 7.2 Write batch evaluation test
    - Multiple evidence items evaluated independently
    - Results don't depend on evaluation order
    - _Requirements: 6.4_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "3.3"] },
    { "id": 3, "tasks": ["4.1", "4.2"] },
    { "id": 4, "tasks": ["4.3", "4.4", "4.5", "4.6", "4.7", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "6.1", "6.2"] },
    { "id": 6, "tasks": ["6.3", "6.4", "7.1"] },
    { "id": 7, "tasks": ["7.2"] }
  ]
}
```

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and error conditions
- All domain objects must be serializable for testing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "3.3"] },
    { "id": 3, "tasks": ["4.1", "4.2"] },
    { "id": 4, "tasks": ["4.3", "4.4", "4.5", "4.6", "4.7", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "6.1", "6.2"] },
    { "id": 6, "tasks": ["6.3", "6.4", "7.1"] },
    { "id": 7, "tasks": ["7.2"] }
  ]
}
```
