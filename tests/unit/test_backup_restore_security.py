import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from postgres_backup_lib import (
    BACKUP_TABLES,
    MANIFEST_SCHEMA,
    RESTORE_CONFIRMATION,
    BackupSecurityError,
    BackupVerificationError,
    assert_backup_source_database_name,
    assert_database_allowed,
    assert_loopback_host,
    assert_maintenance_database,
    assert_restore_database_name,
    assert_test_environment,
    connection_secrets,
    parse_database_url,
    redact,
    resolve_compatible_tool,
    restore_backup,
    verify_manifest,
    write_json_atomic,
)


def make_manifest(tmp_path: Path, backup_path: Path, **overrides) -> dict:
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "created_at": "2026-01-01T00:00:00+00:00",
        "environment": "test",
        "source": {"database": "securecode_backup_source_x", "alembic_head": "d4e9f1a2b3c4"},
        "backup_file": backup_path.name,
        "format": "pg_custom",
        "size_bytes": backup_path.stat().st_size,
        "sha256": hashlib.sha256(backup_path.read_bytes()).hexdigest(),
        "table_fingerprints": {table: {"count": 0, "sha256": "0" * 64} for table in BACKUP_TABLES},
    }
    manifest.update(overrides)
    return manifest


def write_backup(tmp_path: Path) -> Path:
    backup_path = tmp_path / "securecode_test_backup.backup"
    backup_path.write_bytes(b"synthetic-backup-payload")
    return backup_path


def test_database_url_password_is_not_repr_or_str():
    parsed = parse_database_url("postgresql+psycopg2://user:S3cr3t!@localhost:5432/securecode_test")
    assert parsed.password == "S3cr3t!"
    assert "S3cr3t" not in repr(parsed)
    assert "S3cr3t" not in str(parsed)
    assert connection_secrets(parsed) == ["S3cr3t!"]


def test_redact_covers_plain_and_url_encoded_secrets():
    result = redact("password=S3cr3t! encoded=S3cr3t%21", ["S3cr3t!"])
    assert "S3cr3t" not in result
    assert result.count("***") == 2


@pytest.mark.parametrize("host", ["prod.example.com", "10.0.0.5", "db.internal"])
def test_non_loopback_hosts_are_rejected(host):
    with pytest.raises(BackupSecurityError, match="loopback"):
        assert_loopback_host(host)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1"])
def test_loopback_hosts_are_accepted(host):
    assert_loopback_host(host)


def test_database_allowlist_rejects_unidentified_database():
    with pytest.raises(BackupSecurityError, match="allowlist"):
        assert_database_allowed("securecode_prod", ["securecode_test"])


def test_environment_must_be_explicit_test():
    with pytest.raises(BackupSecurityError, match="test"):
        assert_test_environment("production")
    assert_test_environment("test")


@pytest.mark.parametrize("database", ["postgres", "securecode_test"])
def test_maintenance_database_accepts_explicit_test_targets(database):
    assert_maintenance_database(database)


@pytest.mark.parametrize("database", ["securecode_prod", "securecode", "template1"])
def test_maintenance_database_rejects_non_test_targets(database):
    with pytest.raises(BackupSecurityError, match="maintenance"):
        assert_maintenance_database(database)


@pytest.mark.parametrize("database", ["securecode_test", "securecode_prod", "postgres", "restore_test"])
def test_restore_database_name_rejects_production_and_ambiguous_targets(database):
    with pytest.raises(BackupSecurityError, match="securecode_restore"):
        assert_restore_database_name(database)


def test_restore_database_name_accepts_generated_isolated_name():
    assert_restore_database_name("securecode_restore_20261121T120000_ab12cd34")


def test_backup_source_database_name_requires_generated_prefix():
    assert_backup_source_database_name("securecode_backup_source_20261121T120000_ab12cd34")
    with pytest.raises(BackupSecurityError, match="securecode_backup_source"):
        assert_backup_source_database_name("securecode_test")


def test_restore_requires_exact_confirmation(tmp_path: Path):
    with pytest.raises(BackupSecurityError, match=RESTORE_CONFIRMATION):
        restore_backup(
            backup_path=tmp_path / "missing.backup",
            manifest_path=tmp_path / "missing.json",
            target_server_url="postgresql://u:p@127.0.0.1:5432/postgres",
            confirmation="yes",
        )


def test_verify_manifest_detects_corrupted_artifact(tmp_path: Path):
    backup_path = write_backup(tmp_path)
    manifest = make_manifest(tmp_path, backup_path)
    manifest_path = tmp_path / "manifest.json"
    write_json_atomic(manifest_path, manifest)
    original_size = backup_path.stat().st_size
    backup_path.write_bytes(b"x" * original_size)
    with pytest.raises(BackupVerificationError, match="SHA-256"):
        verify_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), backup_path)


def test_verify_manifest_rejects_credentials_in_manifest(tmp_path: Path):
    backup_path = write_backup(tmp_path)
    manifest = make_manifest(tmp_path, backup_path, source={"database": "x", "password": "secret"})
    with pytest.raises(BackupVerificationError, match="forbidden key"):
        verify_manifest(manifest, backup_path)


def test_verify_manifest_rejects_connection_url_value(tmp_path: Path):
    backup_path = write_backup(tmp_path)
    manifest = make_manifest(tmp_path, backup_path, notes="postgresql://prod.example.com/securecode")
    with pytest.raises(BackupVerificationError, match="connection URL"):
        verify_manifest(manifest, backup_path)


def test_verify_manifest_rejects_missing_fingerprints(tmp_path: Path):
    backup_path = write_backup(tmp_path)
    manifest = make_manifest(tmp_path, backup_path, table_fingerprints={"users": {"count": 1}})
    with pytest.raises(BackupVerificationError, match="fingerprints"):
        verify_manifest(manifest, backup_path)


def test_verify_manifest_accepts_valid_synthetic_artifact(tmp_path: Path):
    backup_path = write_backup(tmp_path)
    manifest = make_manifest(
        tmp_path,
        backup_path,
        sha256=hashlib.sha256(backup_path.read_bytes()).hexdigest(),
    )
    verified = verify_manifest(manifest, backup_path)
    assert verified["schema"] == MANIFEST_SCHEMA
    assert verified["alembic_head"] == "d4e9f1a2b3c4"
    assert verified["size_bytes"] == backup_path.stat().st_size


def test_resolve_compatible_tool_prefers_server_major(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pg17 = tmp_path / "pg17"
    pg15 = tmp_path / "pg15"
    pg17.mkdir()
    pg15.mkdir()
    for directory, version in ((pg17, "pg_dump (PostgreSQL) 17.0"), (pg15, "pg_dump (PostgreSQL) 15.0")):
        tool = directory / "pg_dump.exe"
        tool.write_text(f"echo {version}\r\n", encoding="utf-8")

    monkeypatch.setenv("PATH", str(pg17))
    monkeypatch.setattr("postgres_backup_lib.tool_version", lambda path: "pg_dump (PostgreSQL) 17.0" if "pg17" in str(path).replace("\\", "/") else "pg_dump (PostgreSQL) 15.0")
    monkeypatch.setattr("postgres_backup_lib.shutil.which", lambda name: str(pg17 / "pg_dump.exe") if name == "pg_dump" else (str(pg15 / "pg_dump.exe") if name == "pg_dump15" else None))

    resolved = resolve_compatible_tool("pg_dump", server_major=15)
    assert resolved.name in {"pg_dump", "pg_dump.exe"}
    assert "pg15" in str(resolved).replace("\\", "/")


def test_resolve_compatible_tool_rejects_incompatible_major(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pg17 = tmp_path / "pg17"
    pg17.mkdir()
    tool = pg17 / "pg_dump.exe"
    tool.write_text("echo pg_dump (PostgreSQL) 17.0\r\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(pg17))
    monkeypatch.setattr("postgres_backup_lib.tool_version", lambda _path: "pg_dump (PostgreSQL) 17.0")
    monkeypatch.setattr("postgres_backup_lib.shutil.which", lambda name: str(tool) if name in {"pg_dump", "pg_dump15"} else None)

    with pytest.raises(RuntimeError, match="Compatible PostgreSQL tool not found"):
        resolve_compatible_tool("pg_dump", server_major=15)
