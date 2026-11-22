from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

MANIFEST_SCHEMA = "securecode.pg_backup.v1"
RESTORE_CONFIRMATION = "RESTORE_TO_ISOLATED_TEST_DATABASE"
PROTECTED_DATABASES = {
    "postgres",
    "template0",
    "template1",
    "securecode",
    "securecode_test",
    "securecode_prod",
    "securecode_production",
}
BACKUP_TABLES = (
    "enterprise_trial_repositories",
    "enterprise_trial_usages",
    "enterprise_trials",
    "evaluation_records",
    "evidence_records",
    "login_attempts",
    "organization_memberships",
    "organizations",
    "repository_authorizations",
    "service_document_acceptances",
    "subscription_events",
    "user_audit_events",
    "user_finops_settings",
    "user_settings",
    "user_sessions",
    "user_subscriptions",
    "users",
)
BACKUP_SOURCE_DATABASE_PATTERN = re.compile(r"^securecode_backup_source_[A-Za-z0-9_]{1,48}$")
RESTORE_DATABASE_PATTERN = re.compile(r"^securecode_restore_[A-Za-z0-9_]{1,48}$")
FORBIDDEN_MANIFEST_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "dsn",
    "database_url",
    "db_url",
    "conninfo",
    "connection_string",
)


class BackupSecurityError(ValueError):
    pass


class BackupVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedDatabaseUrl:
    scheme: str
    username: str
    password: str = field(repr=False)
    host: str
    port: int
    database: str
    options: dict[str, str] = field(default_factory=dict)


def parse_database_url(value: str) -> ParsedDatabaseUrl:
    split = urlsplit(value.strip())
    if split.scheme not in {"postgresql", "postgresql+psycopg2"}:
        raise BackupSecurityError("A PostgreSQL database URL is required")
    if not split.hostname or not split.username or not split.password:
        raise BackupSecurityError("The database URL must include host, username and password")
    database = split.path.lstrip("/")
    if not database:
        raise BackupSecurityError("The database URL must include a database name")
    options = {key: values[-1] for key, values in parse_qs(split.query).items()}
    return ParsedDatabaseUrl(
        scheme=split.scheme,
        username=split.username,
        password=split.password,
        host=split.hostname,
        port=split.port or 5432,
        database=database,
        options=options,
    )


def sqlalchemy_url(parsed: ParsedDatabaseUrl, database: str | None = None) -> str:
    return URL.create(
        "postgresql+psycopg2",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port,
        database=database or parsed.database,
        query=parsed.options,
    ).render_as_string(hide_password=False)


def redact(value: object, secrets_to_hide: Iterable[str]) -> str:
    result = str(value)
    unique_secrets = {item for item in secrets_to_hide if item}
    for secret in sorted(unique_secrets, key=len, reverse=True):
        result = result.replace(secret, "***")
        result = result.replace(quote(secret, safe=""), "***")
    return result


def connection_secrets(*parsed_values: ParsedDatabaseUrl) -> list[str]:
    return [item.password for item in parsed_values]


def assert_test_environment(environment: str) -> None:
    if environment != "test":
        raise BackupSecurityError("Only the explicit test environment is allowed")


def assert_loopback_host(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise BackupSecurityError("Only loopback database hosts are allowed") from error
    if not address.is_loopback:
        raise BackupSecurityError("Only loopback database hosts are allowed")


def assert_database_allowed(database: str, allowed_databases: Iterable[str]) -> None:
    allowed = {item.strip().lower() for item in allowed_databases if item.strip()}
    if database.lower() not in allowed:
        raise BackupSecurityError("The database name is not in the explicit allowlist")


def assert_maintenance_database(database: str) -> None:
    name = database.lower()
    if name in {"postgres", "securecode_test"}:
        return
    if name in PROTECTED_DATABASES or not name.endswith("_test"):
        raise BackupSecurityError("The maintenance database is not an explicit test target")


def assert_restore_database_name(database: str) -> None:
    if not RESTORE_DATABASE_PATTERN.fullmatch(database):
        raise BackupSecurityError("The restore database must match securecode_restore_<isolated-name>")
    if database.lower() in PROTECTED_DATABASES:
        raise BackupSecurityError("The restore database name is protected")


def assert_backup_source_database_name(database: str) -> None:
    if not BACKUP_SOURCE_DATABASE_PATTERN.fullmatch(database):
        raise BackupSecurityError("The source database must match securecode_backup_source_<isolated-name>")
    if database.lower() in PROTECTED_DATABASES:
        raise BackupSecurityError("The source database name is protected")


def new_backup_source_database_name() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"securecode_backup_source_{stamp}_{secrets.token_hex(4)}"


def new_restore_database_name() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"securecode_restore_{stamp}_{secrets.token_hex(4)}"


def libpq_environment(parsed: ParsedDatabaseUrl, application_name: str) -> dict[str, str]:
    environment = os.environ.copy()
    for key in (
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSFILE",
        "PGHOST",
        "PGPORT",
        "PGDATABASE",
        "PGUSER",
        "PGPASSWORD",
        "PGSSLMODE",
        "PGOPTIONS",
        "PGAPPNAME",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "PGHOST": parsed.host,
            "PGPORT": str(parsed.port),
            "PGDATABASE": parsed.database,
            "PGUSER": parsed.username,
            "PGPASSWORD": parsed.password,
            "PGCONNECT_TIMEOUT": "10",
            "PGAPPNAME": application_name,
        }
    )
    if "sslmode" in parsed.options:
        environment["PGSSLMODE"] = parsed.options["sslmode"]
    return environment


def resolve_tool(name: str, bin_dir: str | None = None) -> Path:
    candidates: list[Path] = []
    if bin_dir:
        directory = Path(bin_dir)
        candidates.extend((directory / name, directory / f"{name}.exe"))
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"Required PostgreSQL tool not found: {name}")


def resolve_compatible_tool(
    name: str,
    *,
    server_major: int | None = None,
    bin_dir: str | None = None,
) -> Path:
    explicit = resolve_tool(name, bin_dir)
    if server_major is None:
        return explicit

    def major_for(candidate: Path) -> int:
        return tool_major(tool_version(candidate))

    try:
        explicit_major = major_for(explicit)
    except (OSError, RuntimeError, ValueError):
        explicit_major = -1
    if explicit_major == server_major:
        return explicit

    versioned = shutil.which(f"{name}{server_major}")
    if versioned:
        candidate = Path(versioned)
        try:
            if major_for(candidate) == server_major:
                return candidate
        except (OSError, RuntimeError, ValueError):
            candidate = None

    common_bins = (
        Path(f"/usr/lib/postgresql/{server_major}/bin"),
        Path(f"/usr/pgsql-{server_major}/bin"),
        Path(f"C:/Program Files/PostgreSQL/{server_major}/bin"),
    )
    for directory in common_bins:
        for candidate in (directory / name, directory / f"{name}.exe"):
            if not candidate.is_file():
                continue
            try:
                if major_for(candidate) == server_major:
                    return candidate
            except (OSError, RuntimeError, ValueError):
                continue

    raise RuntimeError(
        f"Compatible PostgreSQL tool not found for {name}: server major {server_major}, resolved {explicit}"
    )


def run_command(command: list[str], environment: Mapping[str, str], secrets_to_hide: Iterable[str]) -> str:
    result = subprocess.run(
        command,
        env=dict(environment),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = redact(result.stderr.strip() or result.stdout.strip() or "no diagnostic output", secrets_to_hide)
        raise RuntimeError(f"{Path(command[0]).name} failed with exit code {result.returncode}: {detail}")
    return result.stdout


def tool_version(tool: Path) -> str:
    return run_command([str(tool), "--version"], os.environ.copy(), []).strip()


def tool_major(version: str) -> int:
    match = re.search(r"(\d+)", version)
    if not match:
        raise RuntimeError(f"Could not determine PostgreSQL tool version from: {version}")
    return int(match.group(1))


def connect(parsed: ParsedDatabaseUrl, database: str | None = None, autocommit: bool = False):
    return psycopg2.connect(
        host=parsed.host,
        port=parsed.port,
        dbname=database or parsed.database,
        user=parsed.username,
        password=parsed.password,
        sslmode=parsed.options.get("sslmode"),
        connect_timeout=10,
        application_name="securecode-backup-restore",
    )


def server_version(parsed: ParsedDatabaseUrl) -> dict[str, str | int]:
    secrets_to_hide = connection_secrets(parsed)
    try:
        connection = connect(parsed)
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            version = str(cursor.fetchone()[0])
            cursor.execute("SHOW server_version_num")
            version_num = int(cursor.fetchone()[0])
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass
    return {"version": version, "version_num": version_num, "major": int(version.split(".")[0])}


def alembic_head(parsed: ParsedDatabaseUrl) -> str:
    secrets_to_hide = connection_secrets(parsed)
    try:
        connection = connect(parsed)
        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            row = cursor.fetchone()
            if not row:
                raise BackupVerificationError("Alembic version table is empty")
            head = str(row[0])
    except psycopg2.errors.UndefinedTable as error:
        raise BackupVerificationError("Alembic version table is missing") from error
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass
    return head


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def json_default(value: Any) -> str:
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def table_fingerprints(parsed: ParsedDatabaseUrl) -> dict[str, dict[str, Any]]:
    engine = create_engine(sqlalchemy_url(parsed))
    secrets_to_hide = connection_secrets(parsed)
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        missing = sorted(set(BACKUP_TABLES) - existing)
        if missing:
            raise BackupVerificationError(f"Missing expected tables: {', '.join(missing)}")
        results: dict[str, dict[str, Any]] = {}
        with engine.connect() as connection:
            for table in BACKUP_TABLES:
                columns = [item["name"] for item in inspector.get_columns(table)]
                primary_key = inspector.get_pk_constraint(table).get("constrained_columns") or []
                order_columns = primary_key or columns
                order_clause = ", ".join(quote_identifier(item) for item in order_columns)
                rows = connection.execute(
                    text(f"SELECT * FROM {quote_identifier(table)} ORDER BY {order_clause}")
                ).mappings().all()
                payload = [dict(row) for row in rows]
                canonical = json.dumps(
                    payload,
                    default=json_default,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                results[table] = {
                    "count": len(payload),
                    "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                }
        return results
    except BackupVerificationError:
        raise
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        engine.dispose()


def referential_integrity(parsed: ParsedDatabaseUrl) -> dict[str, Any]:
    engine = create_engine(sqlalchemy_url(parsed))
    secrets_to_hide = connection_secrets(parsed)
    try:
        inspector = inspect(engine)
        violations: dict[str, int] = {}
        checked = 0
        with engine.connect() as connection:
            for table in BACKUP_TABLES:
                for foreign_key in inspector.get_foreign_keys(table):
                    child_columns = foreign_key.get("constrained_columns") or []
                    parent_columns = foreign_key.get("referred_columns") or []
                    parent_table = foreign_key.get("referred_table")
                    if not child_columns or not parent_columns or not parent_table:
                        continue
                    checked += 1
                    join_clause = " AND ".join(
                        f"c.{quote_identifier(child)} = p.{quote_identifier(parent)}"
                        for child, parent in zip(child_columns, parent_columns)
                    )
                    required_clause = " AND ".join(
                        f"c.{quote_identifier(child)} IS NOT NULL" for child in child_columns
                    )
                    missing_clause = " OR ".join(
                        f"p.{quote_identifier(parent)} IS NULL" for parent in parent_columns
                    )
                    query = (
                        f"SELECT COUNT(*) FROM {quote_identifier(table)} c "
                        f"LEFT JOIN {quote_identifier(parent_table)} p ON {join_clause} "
                        f"WHERE {required_clause} AND ({missing_clause})"
                    )
                    count = int(connection.execute(text(query)).scalar_one())
                    if count:
                        label = f"{table}.{','.join(child_columns)}->{parent_table}"
                        violations[label] = count
        return {"checked_foreign_keys": checked, "violations": violations}
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        engine.dispose()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_manifest_has_no_credentials(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in FORBIDDEN_MANIFEST_KEY_PARTS):
                raise BackupVerificationError(f"Manifest contains forbidden key: {key}")
            assert_manifest_has_no_credentials(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            assert_manifest_has_no_credentials(nested)
        return
    if isinstance(value, str) and value.startswith(("postgresql://", "postgres://")):
        raise BackupVerificationError("Manifest contains a database connection URL")


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BackupVerificationError("Manifest file does not exist")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BackupVerificationError("Manifest is not valid JSON") from error
    if not isinstance(payload, dict):
        raise BackupVerificationError("Manifest must contain a JSON object")
    return payload


def verify_manifest(manifest: Mapping[str, Any], backup_path: Path) -> dict[str, Any]:
    assert_manifest_has_no_credentials(manifest)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise BackupVerificationError("Unsupported backup manifest schema")
    expected_file = manifest.get("backup_file")
    if expected_file != backup_path.name:
        raise BackupVerificationError("Backup file name does not match the manifest")
    if not backup_path.is_file():
        raise BackupVerificationError("Backup artifact does not exist")
    expected_size = manifest.get("size_bytes")
    expected_sha256 = manifest.get("sha256")
    if not isinstance(expected_size, int) or expected_size < 0:
        raise BackupVerificationError("Manifest size_bytes is invalid")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise BackupVerificationError("Manifest sha256 is invalid")
    actual_size = backup_path.stat().st_size
    actual_sha256 = file_sha256(backup_path)
    if actual_size != expected_size:
        raise BackupVerificationError("Backup artifact size does not match the manifest")
    if actual_sha256 != expected_sha256:
        raise BackupVerificationError("Backup artifact SHA-256 does not match the manifest")
    fingerprints = manifest.get("table_fingerprints")
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(BACKUP_TABLES):
        raise BackupVerificationError("Manifest table fingerprints are incomplete")
    source = manifest.get("source")
    if not isinstance(source, Mapping) or not source.get("alembic_head"):
        raise BackupVerificationError("Manifest source metadata is incomplete")
    return {
        "schema": manifest["schema"],
        "backup_file": backup_path.name,
        "size_bytes": actual_size,
        "sha256": actual_sha256,
        "alembic_head": str(source["alembic_head"]),
        "environment": manifest.get("environment"),
    }


def create_backup(
    *,
    source_url: str,
    output_dir: Path,
    allowed_database: str,
    pg_bin_dir: str | None = None,
    environment: str = "test",
) -> dict[str, Any]:
    started = datetime.now(UTC)
    parsed = parse_database_url(source_url)
    secrets_to_hide = connection_secrets(parsed)
    assert_test_environment(environment)
    assert_loopback_host(parsed.host)
    assert_database_allowed(parsed.database, [allowed_database])

    info = server_version(parsed)
    dump_tool = resolve_compatible_tool("pg_dump", server_major=int(info["major"]), bin_dir=pg_bin_dir)
    dump_version = tool_version(dump_tool)
    if tool_major(dump_version) != int(info["major"]):
        raise RuntimeError("pg_dump major version must match the PostgreSQL server major version")
    head = alembic_head(parsed)
    fingerprints = table_fingerprints(parsed)
    integrity = referential_integrity(parsed)
    if integrity["violations"]:
        raise BackupVerificationError("Source database has referential integrity violations")

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = started.strftime("%Y%m%dT%H%M%S%fZ")
    nonce = secrets.token_hex(3)
    backup_path = output_dir / f"securecode_{environment}_{parsed.database}_{stamp}_{nonce}.backup"
    temporary_path = backup_path.with_name(f".{backup_path.name}.part")
    if backup_path.exists() or temporary_path.exists():
        raise RuntimeError("Refusing to overwrite an existing backup artifact")

    command = [
        str(dump_tool),
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--no-password",
        "--lock-wait-timeout=5",
        "--file",
        str(temporary_path),
    ]
    environment_variables = libpq_environment(parsed, "securecode-backup")
    run_command(command, environment_variables, secrets_to_hide)
    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        raise BackupVerificationError("pg_dump did not produce a non-empty artifact")

    size = temporary_path.stat().st_size
    checksum = file_sha256(temporary_path)
    os.chmod(temporary_path, 0o600)
    os.replace(temporary_path, backup_path)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "created_at": started.isoformat(),
        "environment": environment,
        "source": {
            "database": parsed.database,
            "host_kind": "loopback",
            "server_version": info["version"],
            "server_version_num": info["version_num"],
            "alembic_head": head,
        },
        "backup_file": backup_path.name,
        "format": "pg_custom",
        "size_bytes": size,
        "sha256": checksum,
        "tools": {"pg_dump": dump_version, "pg_dump_major": tool_major(dump_version)},
        "table_fingerprints": fingerprints,
        "referential_integrity": integrity,
    }
    manifest_path = backup_path.with_suffix(".backup.manifest.json")
    write_json_atomic(manifest_path, manifest)
    verify_manifest(load_manifest(manifest_path), backup_path)
    finished = datetime.now(UTC)
    return {
        "status": "ok",
        "backup_file": str(backup_path),
        "manifest_file": str(manifest_path),
        "size_bytes": size,
        "sha256": checksum,
        "alembic_head": head,
        "tables": len(fingerprints),
        "duration_seconds": round((finished - started).total_seconds(), 3),
    }


def database_exists(parsed: ParsedDatabaseUrl, database: str) -> bool:
    secrets_to_hide = connection_secrets(parsed)
    try:
        connection = connect(parsed)
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            return cursor.fetchone() is not None
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass


def create_empty_database(parsed: ParsedDatabaseUrl, database: str) -> None:
    secrets_to_hide = connection_secrets(parsed)
    if database.lower() in PROTECTED_DATABASES:
        raise BackupSecurityError("The database name is protected")
    if database_exists(parsed, database):
        raise BackupVerificationError("Target database already exists; restore was not attempted")
    try:
        connection = connect(parsed)
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    except Exception as error:
        raise RuntimeError(redact(error, secrets_to_hide)) from error
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass


def restore_backup(
    *,
    backup_path: Path,
    manifest_path: Path,
    target_server_url: str,
    pg_bin_dir: str | None = None,
    environment: str = "test",
    confirmation: str = "",
    target_database: str | None = None,
) -> dict[str, Any]:
    started = datetime.now(UTC)
    if confirmation != RESTORE_CONFIRMATION:
        raise BackupSecurityError(f"Confirmation must be exactly {RESTORE_CONFIRMATION}")
    manifest = load_manifest(manifest_path)
    verified = verify_manifest(manifest, backup_path)
    assert_test_environment(environment)
    if verified["environment"] != environment:
        raise BackupSecurityError("Backup environment does not match the requested restore environment")

    server = parse_database_url(target_server_url)
    secrets_to_hide = connection_secrets(server)
    assert_loopback_host(server.host)
    assert_maintenance_database(server.database)

    database = target_database or new_restore_database_name()
    assert_restore_database_name(database)
    if database.lower() == server.database.lower():
        raise BackupSecurityError("Restore target must be different from the maintenance database")

    expected_major = int(manifest["source"]["server_version_num"]) // 10000
    restore_tool = resolve_compatible_tool("pg_restore", server_major=expected_major, bin_dir=pg_bin_dir)
    restore_version = tool_version(restore_tool)
    if tool_major(restore_version) != expected_major:
        raise RuntimeError("pg_restore major version must match the backup server major version")

    target_url = sqlalchemy_url(server, database=database)
    target = parse_database_url(target_url)
    secrets_to_hide.extend(connection_secrets(target))
    create_empty_database(server, database)

    command = [
        str(restore_tool),
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        "--single-transaction",
        "--dbname",
        database,
        str(backup_path),
    ]
    environment_variables = libpq_environment(target, "securecode-restore")
    run_command(command, environment_variables, secrets_to_hide)

    restored_head = alembic_head(target)
    if restored_head != verified["alembic_head"]:
        raise BackupVerificationError("Restored Alembic head does not match the backup manifest")
    restored_fingerprints = table_fingerprints(target)
    expected_fingerprints = manifest["table_fingerprints"]
    mismatches = {
        table: {
            "expected": expected_fingerprints[table],
            "actual": restored_fingerprints[table],
        }
        for table in BACKUP_TABLES
        if expected_fingerprints[table] != restored_fingerprints[table]
    }
    if mismatches:
        raise BackupVerificationError(f"Restored dataset fingerprints differ: {', '.join(sorted(mismatches))}")
    integrity = referential_integrity(target)
    if integrity["violations"]:
        raise BackupVerificationError("Restored database has referential integrity violations")

    finished = datetime.now(UTC)
    return {
        "status": "ok",
        "source_backup": backup_path.name,
        "target_database": database,
        "alembic_head": restored_head,
        "tables_verified": len(restored_fingerprints),
        "foreign_keys_verified": integrity["checked_foreign_keys"],
        "restore_seconds": round((finished - started).total_seconds(), 3),
    }
