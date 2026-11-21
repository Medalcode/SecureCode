import json

from securecode.engine.evaluator import get_rule_definition


def _write_rule(directory, version):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "GH-001.json").write_text(json.dumps({
        "rule_id": "GH-001-RULE",
        "control_id": "GH-001",
        "version": version,
        "active": True,
        "allowlisted_fields": ["required_review_approvals", "dismiss_stale_reviews"],
        "condition": {
            "operator": "AND",
            "conditions": [
                {"field": "required_review_approvals", "operator": "GTE", "value": 2},
                {"field": "dismiss_stale_reviews", "operator": "EQ", "value": True},
            ],
        },
    }), encoding="utf-8")


def test_rule_cache_uses_resolved_directory(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_rule(first, 1)
    _write_rule(second, 2)

    monkeypatch.setenv("SECURECODE_RULES_DIR", str(first))
    assert get_rule_definition("GH-001.json").version == 1

    monkeypatch.setenv("SECURECODE_RULES_DIR", str(second))
    assert get_rule_definition("GH-001.json").version == 2

    monkeypatch.setenv("SECURECODE_RULES_DIR", str(first))
    assert get_rule_definition("GH-001.json").version == 1
