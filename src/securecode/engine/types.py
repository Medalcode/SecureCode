from enum import Enum

class EvaluationStatus(Enum):
    """Status of a rule evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
