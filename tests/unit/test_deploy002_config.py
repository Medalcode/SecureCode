"""
DEPLOY-002 — Unit tests para configuración segura de conexión y seed de usuarios.

Cubre:
  - Normalización de URL de base de datos.
  - Detección de dialecto PostgreSQL vs SQLite.
  - Parámetros de pool activos sólo para PostgreSQL.
  - Comportamiento del seed_user sin credenciales (SystemExit).
  - Comportamiento del seed_user con variables de entorno.
  - Comportamiento del seed_user con getpass interactivo.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Tests: _normalize_database_url y _is_postgres_url
# ---------------------------------------------------------------------------

def test_normalize_postgres_prefix():
    """Prefijo 'postgres://' debe convertirse a 'postgresql://'."""
    from securecode.api.dependencies import _normalize_database_url
    url = "postgres://user:pass@host:5432/db"
    result = _normalize_database_url(url)
    assert result == "postgresql://user:pass@host:5432/db"


def test_normalize_postgresql_prefix_unchanged():
    """Prefijo 'postgresql://' ya válido no debe modificarse."""
    from securecode.api.dependencies import _normalize_database_url
    url = "postgresql://user:pass@host:5432/db"
    result = _normalize_database_url(url)
    assert result == url


def test_normalize_postgresql_psycopg2_unchanged():
    """Prefijo 'postgresql+psycopg2://' no debe modificarse."""
    from securecode.api.dependencies import _normalize_database_url
    url = "postgresql+psycopg2://user:pass@host:5432/db"
    result = _normalize_database_url(url)
    assert result == url


def test_normalize_sqlite_unchanged():
    """URLs SQLite no deben modificarse."""
    from securecode.api.dependencies import _normalize_database_url
    url = "sqlite:///:memory:"
    result = _normalize_database_url(url)
    assert result == url


def test_normalize_postgres_preserves_query_params():
    """Normalización preserva parámetros de query (sslmode=require, etc.)."""
    from securecode.api.dependencies import _normalize_database_url
    url = "postgres://user:pass@host:6543/db?sslmode=require"
    result = _normalize_database_url(url)
    assert result.startswith("postgresql://")
    assert "sslmode=require" in result


def test_is_postgres_url_true_for_postgresql():
    from securecode.api.dependencies import _is_postgres_url
    assert _is_postgres_url("postgresql://user:pass@host/db") is True


def test_is_postgres_url_true_for_psycopg2():
    from securecode.api.dependencies import _is_postgres_url
    assert _is_postgres_url("postgresql+psycopg2://user:pass@host/db") is True


def test_is_postgres_url_false_for_sqlite():
    from securecode.api.dependencies import _is_postgres_url
    assert _is_postgres_url("sqlite:///:memory:") is False


# ---------------------------------------------------------------------------
# Tests: Engine crea con pool_pre_ping para PostgreSQL
# ---------------------------------------------------------------------------

def test_engine_postgres_has_pool_pre_ping(monkeypatch):
    """Para URL PostgreSQL el engine debe tener pool_pre_ping=True."""
    import securecode.api.dependencies as deps
    # Resetear singleton para forzar re-inicialización
    deps._engine = None
    deps._SessionLocal = None

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")

    with patch("securecode.api.dependencies.create_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        with patch("securecode.api.dependencies.sessionmaker"):
            deps.get_engine()

        _, kwargs = mock_create.call_args
        assert kwargs.get("pool_pre_ping") is True, (
            "pool_pre_ping debe ser True para PostgreSQL"
        )
        assert kwargs.get("pool_recycle") == 300, (
            "pool_recycle debe ser 300 s para PostgreSQL"
        )

    # Limpiar singleton para no contaminar otros tests
    deps._engine = None
    deps._SessionLocal = None


def test_engine_sqlite_no_pool_pre_ping(monkeypatch):
    """Para URL SQLite el engine NO debe recibir pool_pre_ping ni pool_recycle."""
    import securecode.api.dependencies as deps
    deps._engine = None
    deps._SessionLocal = None

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    with patch("securecode.api.dependencies.create_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        with patch("securecode.api.dependencies.sessionmaker"):
            deps.get_engine()

        _, kwargs = mock_create.call_args
        assert "pool_pre_ping" not in kwargs, (
            "pool_pre_ping no debe pasarse para SQLite"
        )
        assert "pool_recycle" not in kwargs, (
            "pool_recycle no debe pasarse para SQLite"
        )

    deps._engine = None
    deps._SessionLocal = None


def test_engine_postgres_url_normalized(monkeypatch):
    """get_database_url normaliza 'postgres://' antes de crear el engine."""
    import securecode.api.dependencies as deps
    deps._engine = None
    deps._SessionLocal = None

    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/db")

    url = deps.get_database_url()
    assert url.startswith("postgresql://"), (
        "URL normalizada debe empezar con 'postgresql://'"
    )

    deps._engine = None
    deps._SessionLocal = None


def test_get_database_url_raises_when_missing(monkeypatch):
    """get_database_url debe lanzar ValueError si DATABASE_URL no está configurada."""
    import securecode.api.dependencies as deps
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        deps.get_database_url()


# ---------------------------------------------------------------------------
# Tests: scripts/seed_user._get_credentials
# ---------------------------------------------------------------------------

class TestGetCredentials:
    """Tests de _get_credentials en scripts/seed_user.py."""

    def _import_get_credentials(self):
        """Helper: importar función desde scripts evitando ejecución del __main__."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "seed_user",
            os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "seed_user.py")
        )
        module = importlib.util.module_from_spec(spec)
        # Parchear sys.argv para evitar que el __main__ evalúe los args del test runner
        with patch.object(sys, "argv", ["seed_user.py"]):
            spec.loader.exec_module(module)
        return module._get_credentials

    def test_raises_systemexit_without_credentials(self):
        """Sin variables de entorno ni argumentos debe salir con código 1."""
        get_creds = self._import_get_credentials()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["seed_user.py"]):
                with pytest.raises(SystemExit) as exc_info:
                    get_creds()
                assert exc_info.value.code == 1

    def test_env_vars_both_set(self):
        """Con SEED_USER_EMAIL + SEED_USER_PASSWORD debe retornar el par."""
        get_creds = self._import_get_credentials()

        env = {"SEED_USER_EMAIL": "test@test.com", "SEED_USER_PASSWORD": "secret123"}
        with patch.dict(os.environ, env):
            with patch.object(sys, "argv", ["seed_user.py"]):
                email, pwd = get_creds()
                assert email == "test@test.com"
                assert pwd == "secret123"

    def test_env_password_only_missing_email_exits(self):
        """Con SEED_USER_PASSWORD pero sin email ni arg, debe salir con código 1."""
        get_creds = self._import_get_credentials()

        env = {"SEED_USER_PASSWORD": "secret123"}
        with patch.dict(os.environ, env, clear=True):
            # Eliminar SEED_USER_EMAIL si existe
            os.environ.pop("SEED_USER_EMAIL", None)
            with patch.object(sys, "argv", ["seed_user.py"]):
                with pytest.raises(SystemExit) as exc_info:
                    get_creds()
                assert exc_info.value.code == 1

    def test_arg_email_with_interactive_password(self):
        """Email como argumento + contraseña por getpass debe retornar el par."""
        get_creds = self._import_get_credentials()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SEED_USER_EMAIL", None)
            os.environ.pop("SEED_USER_PASSWORD", None)
            with patch.object(sys, "argv", ["seed_user.py", "user@example.com"]):
                with patch("getpass.getpass", return_value="interactivepass"):
                    email, pwd = get_creds()
                    assert email == "user@example.com"
                    assert pwd == "interactivepass"

    def test_empty_interactive_password_exits(self):
        """Si el usuario ingresa contraseña vacía vía getpass, debe salir con código 1."""
        get_creds = self._import_get_credentials()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SEED_USER_EMAIL", None)
            os.environ.pop("SEED_USER_PASSWORD", None)
            with patch.object(sys, "argv", ["seed_user.py", "user@example.com"]):
                with patch("getpass.getpass", return_value=""):
                    with pytest.raises(SystemExit) as exc_info:
                        get_creds()
                    assert exc_info.value.code == 1

    def test_keyboard_interrupt_during_getpass_exits(self):
        """Si el usuario interrumpe getpass con Ctrl+C, debe salir con código 1."""
        get_creds = self._import_get_credentials()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SEED_USER_EMAIL", None)
            os.environ.pop("SEED_USER_PASSWORD", None)
            with patch.object(sys, "argv", ["seed_user.py", "user@example.com"]):
                with patch("getpass.getpass", side_effect=KeyboardInterrupt):
                    with pytest.raises(SystemExit) as exc_info:
                        get_creds()
                    assert exc_info.value.code == 1
