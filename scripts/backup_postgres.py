from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postgres_backup_lib import (
    BackupSecurityError,
    create_backup,
    load_manifest,
    verify_manifest,
)

from securecode.observability import configure_logging, log_critical_error

configure_logging()


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or verify a SecureCode PostgreSQL backup artifact")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a custom-format backup from an explicit test database")
    create.add_argument("--environment", default="test")
    create.add_argument("--allowed-database", required=True)
    create.add_argument("--output-dir", required=True)
    create.add_argument("--pg-bin-dir", default=os.environ.get("PG_BIN_DIR"))

    verify = subparsers.add_parser("verify", help="Verify checksum, manifest safety and completeness")
    verify.add_argument("--backup", required=True)
    verify.add_argument("--manifest", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            source_url = os.environ.get("BACKUP_SOURCE_DATABASE_URL", "")
            if not source_url:
                raise BackupSecurityError("BACKUP_SOURCE_DATABASE_URL is required")
            result = create_backup(
                source_url=source_url,
                output_dir=Path(args.output_dir).resolve(),
                allowed_database=args.allowed_database,
                pg_bin_dir=args.pg_bin_dir,
                environment=args.environment,
            )
        else:
            backup_path = Path(args.backup).resolve()
            manifest_path = Path(args.manifest).resolve()
            verified = verify_manifest(load_manifest(manifest_path), backup_path)
            result = {"status": "ok", "verification": verified}
    except Exception as error:
        log_critical_error(
            "backup.operation.failed",
            error_type=type(error).__name__,
            operation=f"backup.{args.command}",
        )
        emit({"status": "error", "error": str(error)})
        raise SystemExit(1) from error
    emit(result)


if __name__ == "__main__":
    main()
