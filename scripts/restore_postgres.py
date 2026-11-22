from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postgres_backup_lib import (
    RESTORE_CONFIRMATION,
    BackupSecurityError,
    restore_backup,
)

from securecode.observability import configure_logging, log_critical_error

configure_logging()


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restore a SecureCode backup into a new isolated test database")
    parser.add_argument("--environment", default="test")
    parser.add_argument("--backup", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target-database", help="Optional explicit securecode_restore_<name> database")
    parser.add_argument("--pg-bin-dir", default=os.environ.get("PG_BIN_DIR"))
    parser.add_argument("--confirm", required=True, help=f"Must be exactly {RESTORE_CONFIRMATION}")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        target_url = os.environ.get("RESTORE_TARGET_DATABASE_URL", "")
        if not target_url:
            raise BackupSecurityError("RESTORE_TARGET_DATABASE_URL is required")
        result = restore_backup(
            backup_path=Path(args.backup).resolve(),
            manifest_path=Path(args.manifest).resolve(),
            target_server_url=target_url,
            pg_bin_dir=args.pg_bin_dir,
            environment=args.environment,
            confirmation=args.confirm,
            target_database=args.target_database,
        )
    except Exception as error:
        log_critical_error(
            "backup.restore.failed",
            error_type=type(error).__name__,
            operation="backup.restore",
        )
        emit({"status": "error", "error": str(error)})
        raise SystemExit(1) from error
    emit(result)


if __name__ == "__main__":
    main()
