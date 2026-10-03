from securecode.models.gh001 import GH001Evidence

def test_deterministic_hash_same_evidence():
    ev1 = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    ev2 = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    assert ev1.canonical_hash() == ev2.canonical_hash()

def test_deterministic_hash_different_evidence():
    ev1 = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    ev2 = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=True)
    assert ev1.canonical_hash() != ev2.canonical_hash()

def test_deterministic_hash_unknown_evidence():
    ev1 = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    ev2 = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    assert ev1.canonical_hash() == ev2.canonical_hash()
    
    ev3 = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=None)
    assert ev1.canonical_hash() != ev3.canonical_hash()
