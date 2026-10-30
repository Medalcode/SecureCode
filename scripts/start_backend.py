import os
import sys
import uvicorn
from pathlib import Path

# Cargar variables desde .env si existe
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:TuNuevaClave123@localhost:5432/securecode"
)
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-securecode-inacap-2026-audit"
if not os.environ.get("JWT_ALGORITHM"):
    os.environ["JWT_ALGORITHM"] = "HS256"

if __name__ == "__main__":
    print("Starting SecureCode FastAPI Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("securecode.api.app:app", host="127.0.0.1", port=8000, log_level="info")
