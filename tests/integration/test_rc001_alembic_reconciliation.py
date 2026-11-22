from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from alembic.config import Config
from psycopg2 import OperationalError
from psycopg2.extras import Json
from sqlalchemy import create_engine, inspect

from alembic import command

PG_HOST = os.environ.get("PGHOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PGPORT", "55435"))
PG_USER = os.environ.get("PGUSER", "postgres")
PG_PASSWORD = os.environ.get("PGPASSWORD", "")
ROOT = Path(__file__).resolve().parents[2]
PSQL = Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\17\bin")) / "psql.exe"


def _server_available() -> bool:
    if not PSQL.exists():
        return False
    try:
        psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, dbname="postgres").close()
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def pg15_available():
    if not _server_available():
        pytest.skip("PostgreSQL 15 isolated server required for RC001 reconciliation tests")


def _run(cmd: list[str], cwd: Path = ROOT, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"cmd={cmd}\nrc={proc.returncode}\nstdout=\n{proc.stdout}\nstderr=\n{proc.stderr}")
    return proc


def _ensure_worktree(work: Path, revision: str) -> None:
    """Create a detached worktree robustly, cleaning stale/prunable registrations."""
    if work.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(work)], cwd=ROOT, capture_output=True, text=True, check=False)
        shutil.rmtree(work, ignore_errors=True)
    # Clear stale metadata when a previous run deleted the directory without unregistering it.
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True, text=True, check=False)
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    add = subprocess.run(
        ["git", "worktree", "add", "--force", "--detach", str(work), revision],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if add.returncode != 0:
        # One retry after prune for already-registered/missing worktree races.
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True, text=True, check=False)
        subprocess.run(["git", "worktree", "remove", "--force", str(work)], cwd=ROOT, capture_output=True, text=True, check=False)
        shutil.rmtree(work, ignore_errors=True)
        _run(["git", "worktree", "add", "--force", "--detach", str(work), revision])


def _remove_worktree(work: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(work)], cwd=ROOT, capture_output=True, text=True, check=False)
    shutil.rmtree(work, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True, text=True, check=False)


def _psql(sql: str, db: str = "postgres") -> None:
    cmd = [str(PSQL), "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER, "-d", db, "-v", "ON_ERROR_STOP=1", "-c", sql]
    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD
    _run(cmd, env=env)


def _db_url(db: str) -> str:
    auth = PG_USER
    if PG_PASSWORD:
        auth += f":{PG_PASSWORD}"
    return f"postgresql+psycopg2://{auth}@{PG_HOST}:{PG_PORT}/{db}"


def _alembic_cfg(db: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _db_url(db))
    return cfg


from contextlib import contextmanager


@contextmanager
def _db_env(db: str):
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = _db_url(db)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old


def _new_db(name: str) -> str:
    safe = f"sc_rc001_{name}_{uuid4().hex[:8]}"
    _psql(f"DROP DATABASE IF EXISTS {safe} WITH (FORCE);")
    _psql(f"CREATE DATABASE {safe} OWNER {PG_USER};")
    return safe


def _drop_db(name: str) -> None:
    _psql(f"DROP DATABASE IF EXISTS {name} WITH (FORCE);")


def _connect(db: str):
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, dbname=db)


def _rows(db: str, sql: str, params=None):
    with _connect(db) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _fingerprint(db: str, table: str, cols: list[str] | None = None) -> dict:
    with _connect(db) as conn, conn.cursor() as cur:
        if cols is None:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                (table,),
            )
            cols = [r[0] for r in cur.fetchall()]
        colsql = ", ".join([f'"{c}"' for c in cols])
        cur.execute(f'SELECT {colsql} FROM "{table}" ORDER BY "id"')
        data = [list(r) for r in cur.fetchall()]
    norm = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    return {"count": len(data), "sha256": hashlib.sha256(norm.encode()).hexdigest(), "cols": cols}


def _schema_objects(db: str) -> dict:
    insp = inspect(create_engine(_db_url(db)))
    tables = sorted(insp.get_table_names())
    cols = {
        t: {c["name"]: c for c in insp.get_columns(t)}
        for t in tables
    }
    indexes = {t: insp.get_indexes(t) for t in tables}
    uniques = {t: insp.get_unique_constraints(t) for t in tables}
    fks = {t: insp.get_foreign_keys(t) for t in tables}
    pk = {t: insp.get_pk_constraint(t) for t in tables}
    return {"tables": tables, "cols": cols, "indexes": indexes, "uniques": uniques, "fks": fks, "pk": pk}


def _assert_reconciled_schema(db: str) -> None:
    obj = _schema_objects(db)
    assert "account_action_tokens" in obj["tables"]
    assert "email_verified_at" in obj["cols"]["users"]
    assert obj["cols"]["users"]["email_verified_at"]["nullable"] is True
    token_cols = obj["cols"]["account_action_tokens"]
    expected = {
        "id": False,
        "user_id": False,
        "purpose": False,
        "token_hash": False,
        "expires_at": False,
        "used_at": True,
        "created_at": False,
    }
    assert set(expected) <= set(token_cols)
    for name, nullable in expected.items():
        assert token_cols[name]["nullable"] is nullable
    pk_cols = set(obj["pk"]["account_action_tokens"].get("constrained_columns") or [])
    assert pk_cols == {"id"}
    uq = obj["uniques"]["account_action_tokens"]
    idx = obj["indexes"]["account_action_tokens"]
    assert any(set(u.get("column_names") or []) == {"token_hash"} for u in uq) or any(
        i.get("unique") and set(i.get("column_names") or []) == {"token_hash"} for i in idx
    )
    assert any(set(i.get("column_names") or []) == {"user_id", "purpose"} for i in idx)
    assert any(
        set(fk.get("constrained_columns") or []) == {"user_id"} and fk.get("referred_table") == "users"
        for fk in obj["fks"]["account_action_tokens"]
    )


def _insert_base_data(db: str, include_acceptance: bool = False) -> dict:
    now = datetime.now(UTC)
    ids = {k: str(uuid4()) for k in ["org1", "org2", "u1", "u2", "m1", "m2", "ev1", "ev2", "eval1", "eval2", "acc1"]}
    with _connect(db) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO organizations (id,name,created_at) VALUES (%s,%s,%s),(%s,%s,%s)",
            (ids["org1"], "Org 1", now, ids["org2"], "Org 2", now),
        )
        # email_verified_at may or may not exist depending on scenario
        cur.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='email_verified_at'"
        )
        has_email_verified = cur.fetchone() is not None
        if has_email_verified:
            cur.execute(
                "INSERT INTO users (id,username,password_hash,active,role,created_at,updated_at,email_verified_at) VALUES (%s,%s,%s,true,%s,%s,%s,%s),(%s,%s,%s,true,%s,%s,%s,%s)",
                (ids["u1"], "u1@example.test", "h1", "platform_admin", now, now, now, ids["u2"], "u2@example.test", "h2", "analyst", now, now, now),
            )
        else:
            cur.execute(
                "INSERT INTO users (id,username,password_hash,active,role,created_at,updated_at) VALUES (%s,%s,%s,true,%s,%s,%s),(%s,%s,%s,true,%s,%s,%s)",
                (ids["u1"], "u1@example.test", "h1", "platform_admin", now, now, ids["u2"], "u2@example.test", "h2", "analyst", now, now),
            )
        cur.execute(
            "INSERT INTO organization_memberships (id,organization_id,user_id,role,created_at) VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)",
            (ids["m1"], ids["org1"], ids["u1"], "organization_owner", now, ids["m2"], ids["org2"], ids["u2"], "organization_owner", now),
        )
        cur.execute(
            "INSERT INTO evidence_records (id,control_id,evidence_hash,raw_evidence,collected_at) VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)",
            (ids["ev1"], "GH-001", "a" * 64, Json({"k": 1}), now, ids["ev2"], "GH-002", "b" * 64, Json({"k": 2}), now),
        )
        cur.execute(
            "INSERT INTO evaluation_records (id,control_id,rule_id,rule_version,status,evaluated_at,evidence_id,requested_by_user_id,source_type,source_repository,source_branch) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (ids["eval1"], "GH-001", "GH-001-RULE", 1, "PASS", now, ids["ev1"], ids["u1"], "github", "org/r1", "main", ids["eval2"], "GH-002", "GH-002-RULE", 1, "FAIL", now, ids["ev2"], ids["u2"], "github", "org/r2", "main"),
        )
        if include_acceptance:
            cur.execute(
                "INSERT INTO service_document_acceptances (id,organization_id,user_id,package_id,package_version,document_id,document_version,document_sha256,package_sha256,source_path,acceptance_type,accepted_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (ids["acc1"], ids["org1"], ids["u1"], "SECURECODE-ONBOARDING", "2026-11-20.1", "SERVICE_TERMS", "2026-11-20.1", "0" * 64, "1" * 64, "/legal/terminos", "organization_registration", now),
            )
    return ids


def _assert_fingerprints_equal(before: dict, db: str, tables: list[str]) -> None:
    for table in tables:
        after = _fingerprint(db, table, cols=before[table]["cols"])
        assert after == before[table], f"fingerprint mismatch for {table}"


def test_reconcile_fresh_install(pg15_available):
    db = _new_db("fresh")
    try:
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        _assert_reconciled_schema(db)
        heads = _rows(db, "SELECT version_num FROM alembic_version")
        assert len(heads) == 1
        assert heads[0]["version_num"] == "ab12cd34ef56"
    finally:
        _drop_db(db)


def test_reconcile_from_c1a4d9e7f205_with_data(pg15_available):
    db = _new_db("c1")
    try:
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "c1a4d9e7f205")
        _insert_base_data(db)
        tables = ["organizations", "users", "organization_memberships", "evidence_records", "evaluation_records"]
        before = {t: _fingerprint(db, t) for t in tables}
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        _assert_reconciled_schema(db)
        _assert_fingerprints_equal(before, db, tables)
        # historical backfill policy applies when column was missing before e7b1 path
        verified = _rows(db, "SELECT email_verified_at IS NOT NULL AS ok FROM users")
        assert all(r["ok"] for r in verified)
        assert _rows(db, "SELECT version_num FROM alembic_version")[0]["version_num"] == "ab12cd34ef56"
    finally:
        _drop_db(db)


def test_reconcile_historical_rc001_authentic(pg15_available):
    db = _new_db("hist")
    work = ROOT / f".tmp_phase177_hist_{uuid4().hex[:8]}"
    _ensure_worktree(work, "20206ec16dc9098739f1e5592e56e910001dcdbd")
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = _db_url(db)
        _run([sys.executable, "-m", "alembic", "-c", str(work / "alembic.ini"), "upgrade", "head"], cwd=work, env=env)
        _insert_base_data(db, include_acceptance=True)
        tables = ["organizations", "users", "organization_memberships", "service_document_acceptances", "evidence_records", "evaluation_records"]
        before = {t: _fingerprint(db, t) for t in tables}
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        _assert_reconciled_schema(db)
        _assert_fingerprints_equal(before, db, tables)
        verified = _rows(db, "SELECT email_verified_at IS NOT NULL AS ok FROM users")
        assert all(r["ok"] for r in verified)
        assert _rows(db, "SELECT version_num FROM alembic_version")[0]["version_num"] == "ab12cd34ef56"
    finally:
        _remove_worktree(work)
        _drop_db(db)


def test_reconcile_idempotent_on_already_reconciled(pg15_available):
    db = _new_db("idem")
    try:
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        _insert_base_data(db, include_acceptance=True)
        tables = ["organizations", "users", "organization_memberships", "service_document_acceptances", "evidence_records", "evaluation_records", "account_action_tokens"]
        before = {t: _fingerprint(db, t) for t in tables}
        with _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        _assert_reconciled_schema(db)
        _assert_fingerprints_equal(before, db, tables)
    finally:
        _drop_db(db)


def test_reconcile_fails_safely_on_incompatible_schema(pg15_available):
    db = _new_db("bad")
    work = ROOT / f".tmp_phase177_bad_{uuid4().hex[:8]}"
    _ensure_worktree(work, "20206ec16dc9098739f1e5592e56e910001dcdbd")
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = _db_url(db)
        _run([sys.executable, "-m", "alembic", "-c", str(work / "alembic.ini"), "upgrade", "head"], cwd=work, env=env)
        _insert_base_data(db, include_acceptance=True)
        tables = ["organizations", "users", "organization_memberships", "service_document_acceptances", "evidence_records", "evaluation_records"]
        before = {t: _fingerprint(db, t) for t in tables}
        # Incompatible partial object: wrong type for email_verified_at
        with _connect(db) as conn, conn.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN email_verified_at TEXT")
        with pytest.raises(Exception) as exc, _db_env(db):
            command.upgrade(_alembic_cfg(db), "head")
        assert "RC001 Alembic reconciliation failed" in str(exc.value)
        _assert_fingerprints_equal(before, db, tables)
        obj = _schema_objects(db)
        assert "account_action_tokens" not in obj["tables"]
        col_type = str(obj["cols"]["users"]["email_verified_at"]["type"]).upper()
        assert "TEXT" in col_type or "CHAR" in col_type
        versions = _rows(db, "SELECT version_num FROM alembic_version")
        assert versions[0]["version_num"] == "d4e9f1a2b3c4"
    finally:
        _remove_worktree(work)
        _drop_db(db)
