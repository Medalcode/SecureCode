"""
Script de utilidad para sembrar (seed) un usuario inicial en la base de datos de SecureCode.

SEGURIDAD: Este script NO acepta contraseñas en argumentos CLI para evitar su exposición
en el historial de shell, tablas de procesos (ps aux) y logs de CI/CD.

Modo de uso:
  # Opción 1: Variables de entorno (recomendado para CI/CD y Cloud Run Jobs)
  SEED_USER_EMAIL=auditor@empresa.com SEED_USER_PASSWORD=<contraseña> python scripts/seed_user.py

  # Opción 2: Email en argumento, contraseña por prompt interactivo (desarrollo local)
  python scripts/seed_user.py auditor@empresa.com

Requisito obligatorio:
  La variable de entorno DATABASE_URL debe estar configurada en ambos modos.

Códigos de salida:
  0 — Usuario creado o actualizado exitosamente.
  1 — Error de configuración (falta DATABASE_URL, email o contraseña).
  2 — Error de base de datos.
"""

import sys
import os
import getpass
from uuid import uuid4
from datetime import datetime, timezone

# Asegurar que src/ esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import User
from securecode.api.security import hash_password


def _get_credentials() -> tuple[str, str]:
    """
    Resolve user credentials without accepting passwords as CLI arguments.

    Priority order:
    1. SEED_USER_EMAIL + SEED_USER_PASSWORD environment variables.
    2. First positional CLI argument as email + interactive getpass prompt.

    Returns:
        (email, password) tuple.

    Raises:
        SystemExit(1) if credentials cannot be resolved.
    """
    # Attempt env vars first
    email_env = os.environ.get("SEED_USER_EMAIL", "").strip()
    password_env = os.environ.get("SEED_USER_PASSWORD", "").strip()

    if email_env and password_env:
        return email_env, password_env

    # Attempt positional arg for email + interactive prompt for password
    if len(sys.argv) >= 2:
        email_arg = sys.argv[1].strip()
        if not email_arg:
            print("[ERROR] El argumento de email no puede estar vacío.", file=sys.stderr)
            sys.exit(1)

        if password_env:
            # Env var password takes precedence over interactive prompt
            return email_arg, password_env

        # Interactive prompt — password is never echoed to stdout
        try:
            password_interactive = getpass.getpass(
                prompt=f"Contraseña para '{email_arg}': "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[ERROR] Entrada de contraseña cancelada.", file=sys.stderr)
            sys.exit(1)

        if not password_interactive:
            print("[ERROR] La contraseña no puede estar vacía.", file=sys.stderr)
            sys.exit(1)

        return email_arg, password_interactive

    # No credentials available at all
    print(
        "[ERROR] No se proporcionaron credenciales.\n"
        "        Configure SEED_USER_EMAIL y SEED_USER_PASSWORD, o bien\n"
        "        pase el email como primer argumento: python scripts/seed_user.py <email>",
        file=sys.stderr,
    )
    sys.exit(1)


def seed_user(username: str, password: str) -> None:
    """
    Create or update a user in the SecureCode database.

    Args:
        username: User's email / login identifier.
        password: Plain-text password; hashed with Argon2id before storage.

    Raises:
        SystemExit(1) if DATABASE_URL is missing.
        SystemExit(2) if a database error occurs.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] La variable DATABASE_URL no está configurada.", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    role = os.environ.get("SEED_USER_ROLE", "admin").strip().lower()
    if role not in {"admin", "auditor"}:
        print("[ERROR] SEED_USER_ROLE debe ser 'admin' o 'auditor'.", file=sys.stderr)
        sys.exit(1)

    try:
        existing = session.query(User).filter(User.username == username).first()
        if existing:
            print(f"[INFO] El usuario '{username}' ya existe. Actualizando contraseña...")
            existing.password_hash = hash_password(password)
            existing.active = True
            existing.role = role
        else:
            print(f"[INFO] Creando nuevo usuario '{username}'...")
            new_user = User(
                id=uuid4(),
                username=username,
                password_hash=hash_password(password),
                active=True,
                role=role,
                created_at=datetime.now(timezone.utc),
            )
            session.add(new_user)
        session.commit()
        print(f"[OK] Usuario '{username}' configurado correctamente en la base de datos.")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Error al registrar el usuario: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        session.close()


if __name__ == "__main__":
    email, pwd = _get_credentials()
    seed_user(email, pwd)
