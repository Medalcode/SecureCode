from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config

from alembic import command

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[0]
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

from postgres_backup_lib import (
    RESTORE_CONFIRMATION,
    BackupVerificationError,
    assert_backup_source_database_name,
    assert_loopback_host,
    assert_maintenance_database,
    connection_secrets,
    create_backup,
    create_empty_database,
    load_manifest,
    new_backup_source_database_name,
    parse_database_url,
    redact,
    restore_backup,
    sqlalchemy_url,
    verify_manifest,
)
from seed_backup_fixture import seed_synthetic_dataset
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import Organization


def alembic_config(database_url: str) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def table_counts(database_url: str) -> dict[str, int]:
    from postgres_backup_lib import BACKUP_TABLES, quote_identifier
    from sqlalchemy import text

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                table: int(connection.execute(text(f"SELECT COUNT(*) FROM {quote_identifier(table)}")).scalar_one())
                for table in BACKUP_TABLES
            }
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an isolated end-to-end PostgreSQL backup and restore verification")
    parser.add_argument("--environment", default="test")
    parser.add_argument("--source-database")
    parser.add_argument("--target-database")
    parser.add_argument("--output-dir", default="artifacts/backup-verification")
    parser.add_argument("--pg-bin-dir", default=os.environ.get("PG_BIN_DIR"))
    parser.add_argument("--evidence-file")
    args = parser.parse_args()

    started = datetime.now(UTC)
    maintenance_url = os.environ.get("RESTORE_TARGET_DATABASE_URL", "")
    if not maintenance_url:
        raise SystemExit("RESTORE_TARGET_DATABASE_URL is required")
    maintenance = parse_database_url(maintenance_url)
    secrets_to_hide = connection_secrets(maintenance)
    source_database = args.source_database or new_backup_source_database_name()
    output_dir = Path(args.output_dir).resolve()
    evidence_path = Path(args.evidence_file).resolve() if args.evidence_file else None

    try:
        assert_loopback_host(maintenance.host)
        assert_maintenance_database(maintenance.database)
        assert_backup_source_database_name(source_database)
        create_empty_database(maintenance, source_database)

        source_url = sqlalchemy_url(maintenance, database=source_database)
        os.environ["DATABASE_URL"] = source_url
        config = alembic_config(source_url)
        command.upgrade(config, "head")
        with redirect_stdout(io.StringIO()):
            command.check(config)

        seeded = seed_synthetic_dataset(source_url, source_database, args.environment)
        source_counts = table_counts(source_url)

        backup = create_backup(
            source_url=source_url,
            output_dir=output_dir,
            allowed_database=source_database,
            pg_bin_dir=args.pg_bin_dir,
            environment=args.environment,
        )
        manifest_path = Path(backup["manifest_file"])
        verified = verify_manifest(load_manifest(manifest_path), Path(backup["backup_file"]))

        restored = restore_backup(
            backup_path=Path(backup["backup_file"]),
            manifest_path=manifest_path,
            target_server_url=maintenance_url,
            pg_bin_dir=args.pg_bin_dir,
            environment=args.environment,
            confirmation=RESTORE_CONFIRMATION,
            target_database=args.target_database,
        )
        target_counts = table_counts(sqlalchemy_url(maintenance, database=restored["target_database"]))
        if source_counts != target_counts:
            raise BackupVerificationError("Source and restored table counts differ")

        engine = create_engine(sqlalchemy_url(maintenance, database=source_database))
        try:
            with sessionmaker(bind=engine)() as session:
                organization_count = session.scalar(select(func.count()).select_from(Organization))
        finally:
            engine.dispose()

        result = {
            "status": "ok",
            "environment": args.environment,
            "source_database": source_database,
            "target_database": restored["target_database"],
            "organizations_seeded": int(organization_count or 0),
            "backup": verified,
            "restore": restored,
            "source_table_counts": source_counts,
            "restored_table_counts": target_counts,
            "seeded": seeded,
            "duration_seconds": round((datetime.now(UTC) - started).total_seconds(), 3),
        }
    except Exception as error:
        result = {
            "status": "error",
            "source_database": source_database,
            "error": redact(error, secrets_to_hide),
        }
        if evidence_path:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(1) from error

    if evidence_path:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
