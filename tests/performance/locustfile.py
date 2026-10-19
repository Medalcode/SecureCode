import os
import uuid
from datetime import datetime, timezone
from locust import HttpUser, task, between, events
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.api.security import hash_password
from securecode.adapters.postgres.models import User, Base

DB_URL = os.environ.get("DATABASE_URL")
TEST_USER = "perf_user"
TEST_PASS = "perf_pass123"

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Se ejecuta una sola vez antes de que comience la prueba de carga.
    Inyecta un usuario de pruebas en la base de datos para aislar 
    las peticiones y no contaminar la DB productiva.
    """
    if not DB_URL:
        return
    
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        user = session.query(User).filter_by(username=TEST_USER).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                username=TEST_USER,
                password_hash=hash_password(TEST_PASS),
                active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(user)
            session.commit()

class SecureCodeUser(HttpUser):
    # Tiempo de espera simulado entre tareas de un usuario (1 a 2 segundos)
    wait_time = between(1, 2)
    token = None

    def on_start(self):
        """
        Se ejecuta cada vez que un usuario virtual (VUser) inicia.
        Realizamos el inicio de sesión una sola vez para no distorsionar 
        los resultados del endpoint GH-001 con la carga de CPU de Argon2id.
        """
        response = self.client.post("/api/v1/auth/token", data={
            "username": TEST_USER,
            "password": TEST_PASS
        }, name="/api/v1/auth/token (Login Único)")
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            # Reportar falla si el entorno de pruebas no tiene el usuario
            self.environment.events.request.fire(
                request_type="POST",
                name="auth_setup",
                response_time=0,
                response_length=0,
                exception=Exception(f"Login failed: {response.text}")
            )

    @task(3)
    def health_check(self):
        """Mide la latencia base del framework sin operaciones de I/O pesadas"""
        self.client.get("/health", name="/health (Baseline)")

    @task(7)
    def evaluate_gh001(self):
        """Mide la orquestación, conexión a BD y latencia controlada del Mock de GitHub"""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.post("/api/v1/evaluations/gh-001", json={
            "owner": "Medalcode",
            "repository": "securecode",
            "branch": "main"
        }, headers=headers, name="/api/v1/evaluations/gh-001")
