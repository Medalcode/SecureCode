from pathlib import Path

import pytest

from securecode.config import ConfigurationError, validate_environment

REPO_ROOT = Path(__file__).resolve().parents[2]


BASE_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "sqlite:///:memory:",
    "JWT_SECRET_KEY": "a" * 32,
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "CORS_ORIGINS": "http://localhost:8000",
    "LOGIN_MAX_FAILURES": "5",
    "LOGIN_WINDOW_SECONDS": "900",
    "TRUST_PROXY_HEADERS": "false",
}


def test_validate_environment_accepts_hermetic_development_config():
    validated = validate_environment(BASE_ENV)

    assert validated.app_env == "development"
    assert validated.database_url == "sqlite:///:memory:"
    assert validated.cors_origins == ("http://localhost:8000",)
    assert validated.login_max_failures == 5
    assert validated.login_window_seconds == 900
    assert validated.trust_proxy_headers is False
    assert validated.github_token_configured is False
    assert validated.seed_user_configured is False
    assert validated.log_level == "INFO"


def test_validate_environment_accepts_production_config():
    env = {
        **BASE_ENV,
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@db.internal:5432/securecode?sslmode=require",
        "CORS_ORIGINS": "https://securecode.example.org,https://admin.example.org",
        "GITHUB_TOKEN": "ghs_" + "b" * 36,
    }

    validated = validate_environment(env)

    assert validated.app_env == "production"
    assert validated.github_token_configured is True
    assert validated.cors_origins == (
        "https://securecode.example.org",
        "https://admin.example.org",
    )


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"DATABASE_URL": ""}, "DATABASE_URL is required"),
        ({"JWT_SECRET_KEY": "short"}, "at least 32 characters"),
        ({"JWT_ALGORITHM": "RS256"}, "JWT_ALGORITHM must be HS256"),
        ({"LOGIN_MAX_FAILURES": "0"}, "LOGIN_MAX_FAILURES must be greater than zero"),
        ({"LOGIN_WINDOW_SECONDS": "abc"}, "LOGIN_WINDOW_SECONDS must be an integer"),
        ({"TRUST_PROXY_HEADERS": "maybe"}, "TRUST_PROXY_HEADERS must be a boolean value"),
        ({"LOG_LEVEL": "TRACE"}, "LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO or DEBUG"),
    ],
)
def test_validate_environment_rejects_invalid_common_values(override, message):
    with pytest.raises(ConfigurationError) as exc:
        validate_environment({**BASE_ENV, **override})

    assert message in str(exc.value)
    assert all(
        str(value) not in issue
        for value in override.values()
        if len(str(value)) > 3
        for issue in exc.value.issues
    )


def test_validate_environment_rejects_production_cors_wildcard():
    env = {
        **BASE_ENV,
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@db.internal:5432/securecode",
        "CORS_ORIGINS": "*",
        "GITHUB_TOKEN": "ghs_" + "b" * 36,
    }

    with pytest.raises(ConfigurationError, match="wildcard origins"):
        validate_environment(env)


def test_validate_environment_rejects_production_without_github_token():
    env = {
        **BASE_ENV,
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@db.internal:5432/securecode",
        "CORS_ORIGINS": "https://securecode.example.org",
    }

    with pytest.raises(ConfigurationError, match="GITHUB_TOKEN is required"):
        validate_environment(env)


def test_validate_environment_rejects_partial_seed_configuration():
    with pytest.raises(ConfigurationError, match="must be set together"):
        validate_environment({**BASE_ENV, "SEED_USER_EMAIL": "admin@example.org"})


def test_validate_environment_rejects_placeholder_secret_in_production():
    env = {
        **BASE_ENV,
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://user:CHANGE_ME@db.internal:5432/securecode",
        "CORS_ORIGINS": "https://securecode.example.org",
        "GITHUB_TOKEN": "ghs_" + "b" * 36,
    }

    with pytest.raises(ConfigurationError, match="placeholder credentials"):
        validate_environment(env)


def test_docker_compose_propagates_startup_validation_variables():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for name in (
        "APP_ENV",
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "CORS_ORIGINS",
        "LOGIN_MAX_FAILURES",
        "LOGIN_WINDOW_SECONDS",
        "TRUST_PROXY_HEADERS",
        "LOG_LEVEL",
    ):
        assert f"{name}:" in compose


def test_workflows_use_consistent_github_token_variable():
    workflow = (REPO_ROOT / ".github/workflows/gh001-e2e.yml").read_text(encoding="utf-8")

    assert "GITHUB_TOKEN: ${{ secrets.VALIDATION_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}" in workflow
    assert "VALIDATION_GITHUB_TOKEN: ${{ secrets." not in workflow
    assert "APP_ENV: test" in workflow
