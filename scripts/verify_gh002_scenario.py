import os
import sys
import json
import getpass
import urllib.request
import urllib.parse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

EXPECTED = {
    "PASS": True,
    "FAIL": False,
    "UNKNOWN": None,
}

if len(sys.argv) != 2 or sys.argv[1].upper() not in EXPECTED:
    raise SystemExit("Uso: python scripts/verify_gh002_scenario.py PASS|FAIL|UNKNOWN")

scenario = sys.argv[1].upper()
db_url = os.environ["DATABASE_URL"]
parsed = make_url(db_url)

assert parsed.database == "securecode_test", "Base incorrecta"
assert parsed.host in ("localhost", "127.0.0.1"), "Host no local"
assert parsed.port == 5432, "Puerto incorrecto"

engine = create_engine(db_url)

with engine.connect() as conn:
    assert conn.execute(
        text("SELECT current_database()")
    ).scalar_one() == "securecode_test"

try:
    password = os.environ.get("PERF_PASS") or getpass.getpass("Contrasena de perf_user: ")
except Exception:
    password = os.environ.get("PERF_PASS", "perf_pass123")

login_data = urllib.parse.urlencode({
    "username": "perf_user",
    "password": password
}).encode()

login_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/token",
    data=login_data,
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    method="POST"
)

with urllib.request.urlopen(login_req, timeout=15) as response:
    token = json.load(response)["access_token"]

payload = json.dumps({
    "owner": "Medalcode",
    "repository": "securecode"
}).encode()

eval_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/evaluations/gh-002",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    },
    method="POST"
)

with urllib.request.urlopen(eval_req, timeout=20) as response:
    http_status = response.status
    result = json.load(response)

evaluation_id = result["evaluation_id"]

with engine.connect() as conn:
    record = conn.execute(text("""
        SELECT
            e.id,
            e.status,
            e.evidence_id,
            v.id,
            v.evidence_hash,
            v.raw_evidence
        FROM evaluation_records e
        JOIN evidence_records v
            ON e.evidence_id = v.id
        WHERE e.id = CAST(:id AS UUID)
          AND e.control_id = 'GH-002'
          AND v.control_id = 'GH-002'
    """), {"id": evaluation_id}).one()

assert http_status == 200, f"Estado HTTP inesperado: {http_status}"
assert result["status"] == scenario, f"Estado evaluacion {result['status']} != {scenario}"
assert record[1] == scenario, f"Estado persistido {record[1]} != {scenario}"
assert record[2] == record[3], "Relacion de evidencia incorrecta"
assert record[4] == result["evidence"]["hash"], "Hash de evidencia inconsistente"
assert record[5]["protection_enabled"] == EXPECTED[scenario], f"protection_enabled {record[5]['protection_enabled']} != {EXPECTED[scenario]}"

print(f"ESCENARIO: {scenario}")
print(f"ESTADO HTTP: {http_status}")
print(f"ESTADO EVALUACION: {result['status']}")
print(f"PROTECTION_ENABLED: {record[5]['protection_enabled']}")
print("RELACION EVIDENCIA: OK")
print("HASH SHA-256: OK")
print(f"GH-002 {scenario}: PASS")
