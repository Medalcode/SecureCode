import logging
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import backup_postgres
import restore_postgres


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _capture_logs() -> tuple[logging.Logger, _ListHandler, int, bool, bool, int]:
    logger = logging.getLogger("securecode.observability")
    handler = _ListHandler()
    previous_level = logger.level
    previous_propagate = logger.propagate
    previous_disabled = logger.disabled
    previous_global_disable = logging.root.manager.disable
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    logger.disabled = False
    logging.disable(logging.NOTSET)
    return logger, handler, previous_level, previous_propagate, previous_disabled, previous_global_disable


def _release_logs(
    logger: logging.Logger,
    handler: _ListHandler,
    level: int,
    propagate: bool,
    disabled: bool,
    global_disable: int,
) -> None:
    logger.removeHandler(handler)
    logger.setLevel(level)
    logger.propagate = propagate
    logger.disabled = disabled
    logging.disable(global_disable)


def test_backup_cli_logs_structured_critical_error(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup_postgres.py", "verify", "--backup", "missing.backup", "--manifest", "missing.json"],
    )
    logger, handler, level, propagate, disabled, global_disable = _capture_logs()

    try:
        with pytest.raises(SystemExit):
            backup_postgres.main()
    finally:
        _release_logs(logger, handler, level, propagate, disabled, global_disable)

    record = next(
        item
        for item in handler.records
        if getattr(item, "event", None) == "backup.operation.failed"
    )
    assert record.levelno == logging.ERROR
    assert getattr(record, "operation", None) == "backup.verify"
    assert getattr(record, "error_type", None) == "BackupVerificationError"


def test_restore_cli_logs_structured_critical_error(monkeypatch):
    monkeypatch.delenv("RESTORE_TARGET_DATABASE_URL", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "restore_postgres.py",
            "--backup",
            "missing.backup",
            "--manifest",
            "missing.json",
            "--confirm",
            "RESTORE_TO_ISOLATED_TEST_DATABASE",
        ],
    )
    logger, handler, level, propagate, disabled, global_disable = _capture_logs()

    try:
        with pytest.raises(SystemExit):
            restore_postgres.main()
    finally:
        _release_logs(logger, handler, level, propagate, disabled, global_disable)

    record = next(
        item
        for item in handler.records
        if getattr(item, "event", None) == "backup.restore.failed"
    )
    assert record.levelno == logging.ERROR
    assert getattr(record, "operation", None) == "backup.restore"
    assert getattr(record, "error_type", None) == "BackupSecurityError"
