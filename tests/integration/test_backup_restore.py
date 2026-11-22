import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from postgres_backup_lib import (
    connection_secrets,
    parse_database_url,
    resolve_tool,
)

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def backup_verification(tmp_path_factory):
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url or "sqlite" in database_url:
        if os.environ.get("REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("DATABASE_URL must be configured for PostgreSQL backup verification")
        pytest.skip("PostgreSQL backup verification requires DATABASE_URL")
    try:
        resolve_tool("pg_dump", os.environ.get("PG_BIN_DIR"))
        resolve_tool("pg_restore", os.environ.get("PG_BIN_DIR"))
    except RuntimeError:
        pytest.skip("pg_dump and pg_restore are required for backup verification")

    workspace = tmp_path_factory.mktemp("backup_restore_e2e")
    evidence_file = workspace / "backup-verification.json"
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_backup_restore.py"),
        "--output-dir",
        str(workspace / "backups"),
        "--evidence-file",
        str(evidence_file),
    ]
    pg_bin_dir = os.environ.get("PG_BIN_DIR")
    if pg_bin_dir:
        command.extend(("--pg-bin-dir", pg_bin_dir))

    environment = os.environ.copy()
    environment["RESTORE_TARGET_DATABASE_URL"] = database_url
    environment.pop("BACKUP_SOURCE_DATABASE_URL", None)
    completed = subprocess.run(command, cwd=REPO_ROOT, env=environment, capture_output=True, text=True, check=False)
    stdout = completed.stdout
    json_start = stdout.find("{")
    payload = json.loads(stdout[json_start:] if json_start >= 0 else stdout)
    assert completed.returncode == 0, redact_output(payload.get("error", ""), database_url)
    return payload, evidence_file


def redact_output(value: str, database_url: str) -> str:
    try:
        secrets = connection_secrets(parse_database_url(database_url))
    except ValueError:
        secrets = []
    for secret in secrets:
        value = value.replace(secret, "***")
    return value


def test_backup_restore_end_to_end_isolation(backup_verification):
    payload, _evidence_file = backup_verification
    assert payload["status"] == "ok"
    assert payload["environment"] == "test"
    assert payload["source_database"].startswith("securecode_backup_source_")
    assert payload["target_database"].startswith("securecode_restore_")
    assert payload["source_database"] != payload["target_database"]
    assert payload["organizations_seeded"] == 2
    assert payload["seeded"]["evaluations"] == 6
    assert payload["seeded"]["acceptances"] == 4
    assert payload["seeded"]["sessions"] == 2
    assert payload["source_table_counts"] == payload["restored_table_counts"]
    assert payload["backup"]["alembic_head"] == "ab12cd34ef56"
    assert payload["restore"]["tables_verified"] == 17
    assert payload["restore"]["foreign_keys_verified"] > 0


def test_backup_restore_evidence_has_no_credentials(backup_verification):
    payload, evidence_file = backup_verification
    database_url = os.environ.get("DATABASE_URL", "")
    evidence_text = evidence_file.read_text(encoding="utf-8")
    secrets = connection_secrets(parse_database_url(database_url)) if database_url else []
    assert all(secret not in evidence_text for secret in secrets)
    assert "password" not in payload["backup"]
    assert "database_url" not in json.dumps(payload).lower()
