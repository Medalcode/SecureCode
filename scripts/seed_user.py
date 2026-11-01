"""
Script de utilidad para sembrar (seed) un usuario en la base de datos PostgreSQL de SecureCode.
Uso:
  python scripts/seed_user.py <username> <password>
Ejemplo:
  python scripts/seed_user.py auditor@empresa.com securecode2026!
"""

import sys
import os
from uuid import uuid4
from datetime import datetime, timezone

# Asegurar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import User
from securecode.api.security import hash_password

def seed_user(username: str, password: str):
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] La variable DATABASE_URL no está configurada.")
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing = session.query(User).filter(User.username == username).first()
        if existing:
            print(f"[INFO] El usuario '{username}' ya existe. Actualizando contraseña...")
            existing.password_hash = hash_password(password)
            existing.active = True
        else:
            print(f"[INFO] Creando nuevo usuario '{username}'...")
            new_user = User(
                id=uuid4(),
                username=username,
                password_hash=hash_password(password),
                active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
        session.commit()
        print(f"[OK] Usuario '{username}' configurado correctamente en la base de datos.")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Error al registrar el usuario: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        user = "auditor@empresa.com"
        pwd = "securecode2026!"
        print(f"[AVISO] Argumentos no provistos. Usando credenciales por defecto: {user}")
    else:
        user = sys.argv[1]
        pwd = sys.argv[2]
    seed_user(user, pwd)
