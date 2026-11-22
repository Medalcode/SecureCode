from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

ALLOWED_APP_ENVS = frozenset({"development", "staging", "production", "test"})
ALLOWED_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})
PLACEHOLDER_TOKENS = ("change_me", "changeme", "change-me", "example", "todo")
POSTGRES_PREFIXES = ("postgresql://", "postgresql+psycopg2://", "postgres://")
SQLITE_PREFIX = "sqlite://"


@dataclass(frozen=True)
class ConfigurationError(Exception):
    issues: tuple[str, ...]

    def __str__(self) -> str:
        return "Invalid environment configuration: " + "; ".join(self.issues)


@dataclass(frozen=True)
class ValidatedEnvironment:
    app_env: str
    database_url: str
    cors_origins: tuple[str, ...]
    login_max_failures: int
    login_window_seconds: int
    trust_proxy_headers: bool
    trusted_proxy_cidrs: tuple[str, ...]
    github_token_configured: bool
    seed_user_configured: bool
    log_level: str


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower().replace("-", "_")
    return any(token.replace("-", "_") in normalized for token in PLACEHOLDER_TOKENS)


def _positive_int(env: Mapping[str, str], name: str, default: str, issues: list[str]) -> int:
    raw = env.get(name, default).strip()
    try:
        value = int(raw)
    except ValueError:
        issues.append(f"{name} must be an integer")
        return 0
    if value <= 0:
        issues.append(f"{name} must be greater than zero")
        return 0
    return value


def _parse_bool(env: Mapping[str, str], name: str, default: bool, issues: list[str]) -> bool:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    issues.append(f"{name} must be a boolean value")
    return default


def _validate_log_level(env: Mapping[str, str], issues: list[str]) -> str:
    raw = env.get("LOG_LEVEL", "INFO").strip().upper()
    if not raw:
        return "INFO"
    if raw not in ALLOWED_LOG_LEVELS:
        issues.append("LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO or DEBUG")
        return "INFO"
    return raw


def _validate_database_url(
    env: Mapping[str, str], app_env: str, issues: list[str]
) -> str:
    database_url = env.get("DATABASE_URL", "").strip().rstrip("\r\n")
    if not database_url:
        issues.append("DATABASE_URL is required")
        return ""
    if database_url.startswith(SQLITE_PREFIX) and app_env not in {"development", "test"}:
        issues.append("DATABASE_URL must be PostgreSQL outside development and test")
    elif not database_url.startswith(POSTGRES_PREFIXES) and not database_url.startswith(SQLITE_PREFIX):
        issues.append("DATABASE_URL must be a PostgreSQL or SQLite URL")
    if app_env in {"production", "staging"} and _is_placeholder(database_url):
        issues.append("DATABASE_URL must not contain placeholder credentials")
    return database_url


def _validate_jwt(env: Mapping[str, str], issues: list[str]) -> None:
    secret = env.get("JWT_SECRET_KEY", "").strip()
    if not secret:
        issues.append("JWT_SECRET_KEY is required")
    elif len(secret) < 32:
        issues.append("JWT_SECRET_KEY must contain at least 32 characters")
    elif _is_placeholder(secret):
        issues.append("JWT_SECRET_KEY must not be a placeholder")
    if env.get("JWT_ALGORITHM", "HS256").strip() != "HS256":
        issues.append("JWT_ALGORITHM must be HS256")


def _validate_cors(env: Mapping[str, str], app_env: str, issues: list[str]) -> tuple[str, ...]:
    origins = tuple(
        origin.strip()
        for origin in env.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    if app_env not in {"production", "staging"}:
        return origins
    if not origins:
        issues.append("CORS_ORIGINS is required in production and staging")
    if "*" in origins:
        issues.append("CORS_ORIGINS must not contain wildcard origins in production or staging")
    if any(not origin.startswith("https://") for origin in origins):
        issues.append("CORS_ORIGINS must use HTTPS in production and staging")
    return origins


def _validate_credentials(env: Mapping[str, str], app_env: str, issues: list[str]) -> tuple[bool, bool]:
    github_token = env.get("GITHUB_TOKEN", "").strip()
    github_token_configured = bool(github_token)
    if app_env in {"production", "staging"} and not github_token_configured:
        issues.append("GITHUB_TOKEN is required in production and staging")
    if github_token and _is_placeholder(github_token):
        issues.append("GITHUB_TOKEN must not be a placeholder")

    seed_email = env.get("SEED_USER_EMAIL", "").strip()
    seed_password = env.get("SEED_USER_PASSWORD", "").strip()
    seed_user_configured = bool(seed_email or seed_password)
    if bool(seed_email) != bool(seed_password):
        issues.append("SEED_USER_EMAIL and SEED_USER_PASSWORD must be set together")
    if app_env in {"production", "staging"} and seed_user_configured and _is_placeholder(seed_password):
        issues.append("SEED_USER_PASSWORD must not be a placeholder in production or staging")
    return github_token_configured, seed_user_configured


def _validate_trusted_proxy_cidrs(env: Mapping[str, str], issues: list[str]) -> tuple[str, ...]:
    raw = env.get("TRUSTED_PROXY_CIDRS", "")
    cidrs = tuple(item.strip() for item in raw.split(",") if item.strip())
    for cidr in cidrs:
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            issues.append("TRUSTED_PROXY_CIDRS must contain valid IP addresses or CIDR ranges")
            break
    return cidrs


def _validate_optional_services(env: Mapping[str, str], app_env: str, issues: list[str]) -> None:
    sentry_dsn = env.get("SENTRY_DSN", "").strip()
    if sentry_dsn and not sentry_dsn.startswith("https://"):
        issues.append("SENTRY_DSN must use HTTPS when configured")
    _parse_bool(env, "PROMETHEUS_ENABLED", False, issues)

    for name in ("POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD"):
        value = env.get(name, "").strip()
        if not value:
            continue
        if name == "POSTGRES_PASSWORD" and app_env in {"production", "staging"} and _is_placeholder(value):
            issues.append("POSTGRES_PASSWORD must not be a placeholder in production or staging")
    if any(env.get(name, "").strip() for name in ("POSTGRES_USER", "POSTGRES_DB")) and not env.get(
        "POSTGRES_PASSWORD", ""
    ).strip():
        issues.append("POSTGRES_PASSWORD is required when POSTGRES_USER or POSTGRES_DB is set")


def validate_environment(environ: Mapping[str, str] | None = None) -> ValidatedEnvironment:
    env = dict(os.environ if environ is None else environ)
    issues: list[str] = []

    app_env = env.get("APP_ENV", "development").strip().lower() or "development"
    if app_env not in ALLOWED_APP_ENVS:
        issues.append("APP_ENV must be development, staging, production or test")

    database_url = _validate_database_url(env, app_env, issues)
    _validate_jwt(env, issues)
    cors_origins = _validate_cors(env, app_env, issues)
    login_max_failures = _positive_int(env, "LOGIN_MAX_FAILURES", "5", issues)
    login_window_seconds = _positive_int(env, "LOGIN_WINDOW_SECONDS", "900", issues)
    trust_proxy_headers = _parse_bool(env, "TRUST_PROXY_HEADERS", False, issues)
    trusted_proxy_cidrs = _validate_trusted_proxy_cidrs(env, issues)
    if trust_proxy_headers and not trusted_proxy_cidrs:
        issues.append("TRUSTED_PROXY_CIDRS is required when TRUST_PROXY_HEADERS=true")
    github_token_configured, seed_user_configured = _validate_credentials(env, app_env, issues)
    log_level = _validate_log_level(env, issues)
    _validate_optional_services(env, app_env, issues)

    if urlparse(database_url).scheme and " " in database_url:
        issues.append("DATABASE_URL must not contain whitespace")

    if issues:
        raise ConfigurationError(tuple(issues))

    return ValidatedEnvironment(
        app_env=app_env,
        database_url=database_url,
        cors_origins=cors_origins,
        login_max_failures=login_max_failures,
        login_window_seconds=login_window_seconds,
        trust_proxy_headers=trust_proxy_headers,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
        github_token_configured=github_token_configured,
        seed_user_configured=seed_user_configured,
        log_level=log_level,
    )
