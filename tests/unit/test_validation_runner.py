import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from scripts.validate_gh001_real import main
from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence

@pytest.fixture
def mock_env_no_token():
    with patch.dict(os.environ, {}, clear=True):
        yield

@pytest.fixture
def mock_env_with_token():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}, clear=True):
        yield

@pytest.fixture
def mock_ground_truth(tmp_path):
    # Create a fake ground truth structure
    gt_data = {
        "cases": [
            {
                "case_id": "GT-TEST-01",
                "repository": "owner/repo",
                "branch": "main",
                "expected_status": "PASS"
            }
        ]
    }
    # We must patch the path in the script to use our tmp_path
    with patch("scripts.validate_gh001_real.Path") as mock_path:
        mock_repo_root = MagicMock()
        mock_repo_root.parent = MagicMock()
        
        # mock the gt_path
        mock_gt_path = tmp_path / "gh001_ground_truth.json"
        with open(mock_gt_path, "w", encoding="utf-8") as f:
            json.dump(gt_data, f)
            
        mock_repo_root.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_gt_path
        
        # mock artifacts dir
        mock_artifacts_dir = tmp_path / "artifacts"
        mock_repo_root.__truediv__.return_value = mock_artifacts_dir
        
        # When Path(__file__).parent.parent is called, return mock_repo_root
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = mock_repo_root
        mock_path.return_value = mock_path_instance
        
        yield mock_artifacts_dir

def test_validation_runner_no_token_exits(mock_env_no_token, capsys):
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0
    out, _ = capsys.readouterr()
    assert "REAL VALIDATION BLOCKED - GITHUB_TOKEN NOT AVAILABLE" in out

@patch("scripts.validate_gh001_real.get_gh001_evidence")
def test_validation_runner_executes(mock_get_evidence, mock_env_with_token, mock_ground_truth, capsys):
    # Setup mock to return a passing evidence
    mock_get_evidence.return_value = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    
    main()
    
    # Check output
    out, _ = capsys.readouterr()
    assert "Starting REAL GitHub validation" in out
    assert "[GT-TEST-01] Expected: PASS | Actual: PASS | Match: True" in out
    
    # Verify artifact
    artifacts_dir = mock_ground_truth
    artifact_file = artifacts_dir / "gh001_real_validation.json"
    assert artifact_file.exists()
    
    with open(artifact_file, "r") as f:
        data = json.load(f)
        
    assert data["summary"]["total"] == 1
    assert data["summary"]["matched"] == 1
    assert data["summary"]["accuracy"] == 1.0
    assert data["cases"][0]["actual_status"] == "PASS"
