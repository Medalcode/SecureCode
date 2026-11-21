from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final
from uuid import uuid4

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from securecode.config import ConfigurationError, validate_environment

SERVICE_NAME = "securecode"
REQUEST_ID_HEADER = "X-Request-ID"
READINESS_TIMEOUT_MS = 250

_LOG_LEVELS: Final[frozenset[str]] = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})
_ENVIRONMENTS: Final[frozenset[str]] = frozenset({"development", "staging", "production", "test"})
_REQUEST_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_LABEL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_.:/{}-]{1,96}$")
_SENSITIVE_VALUE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:bearer\s+\S+|[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|://|password|secret|token|authorization|cookie)",
    re.IGNORECASE,
)
_SAFE_LOG_FIELDS: Final[tuple[str, ...]] = (
    "method",
    "route",
    "status_code",
    "duration_ms",
    "error_type",
    "control_id",
    "result_status",
    "outcome",
    "reason",
    "phase",
    "operation",
    "from_cache",
    "check",
    "attempt",
)
_HTTP_METHODS: Final[frozenset[str]] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_CONTROL_IDS: Final[frozenset[str]] = frozenset({"GH-001", "GH-002", "GH-003"})
_RESULT_STATUSES: Final[frozenset[str]] = frozenset({"PASS", "FAIL", "UNKNOWN", "NONE"})
_OUTCOMES: Final[frozenset[str]] = frozenset({"RESULT", "TECHNICAL_ERROR", "OTHER"})
_DURATION_BUCKETS_MS: Final[tuple[float, ...]] = (50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0)

_request_id_var: ContextVar[str] = ContextVar("securecode_request_id", default="-")
_marker_handler_attribute = "_securecode_json_formatter"


def resolve_request_id(raw_value: str | None) -> str:
    if isinstance(raw_value, str) and _REQUEST_ID_PATTERN.fullmatch(raw_value):
        return raw_value
    return uuid4().hex


def bind_request_id(request_id: str) -> Token[str]:
    return _request_id_var.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str:
    return _request_id_var.get()


@contextmanager
def request_id_context(request_id: str) -> Iterator[None]:
    token = bind_request_id(request_id)
    try:
        yield
    finally:
        reset_request_id(token)


def _current_environment(environ: Mapping[str, str] | None = None) -> str:
    env = dict(os.environ if environ is None else environ)
    value = env.get("APP_ENV", "development").strip().lower()
    return value if value in _ENVIRONMENTS else "unknown"


def _sanitize_log_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, (dict, list, tuple, set)):
        return "[redacted]"
    text_value = str(value).strip()
    if not text_value:
        return None
    if len(text_value) > 128 or _SENSITIVE_VALUE_PATTERN.search(text_value):
        return "[redacted]"
    return text_value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "event": _sanitize_log_value(getattr(record, "event", "log.message")) or "log.message",
            "service": SERVICE_NAME,
            "environment": _current_environment(),
            "request_id": _request_id_var.get(),
        }
        for field_name in _SAFE_LOG_FIELDS:
            if hasattr(record, field_name):
                sanitized = _sanitize_log_value(getattr(record, field_name))
                if sanitized is not None:
                    payload[field_name] = sanitized
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(environ: Mapping[str, str] | None = None) -> None:
    env = dict(os.environ if environ is None else environ)
    level = env.get("LOG_LEVEL", "INFO").strip().upper()
    if level not in _LOG_LEVELS:
        level = "INFO"
    numeric_level = getattr(logging, level)

    root = logging.getLogger()
    handler = next(
        (existing for existing in root.handlers if getattr(existing, _marker_handler_attribute, False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        setattr(handler, _marker_handler_attribute, True)
        root.addHandler(handler)
    handler.setFormatter(JsonFormatter())
    root.setLevel(numeric_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        named_logger = logging.getLogger(logger_name)
        if handler not in named_logger.handlers:
            named_logger.addHandler(handler)
        named_logger.propagate = False
        named_logger.setLevel(numeric_level)


def log_event(level: int, event: str, **fields: Any) -> None:
    logging.getLogger("securecode.observability").log(
        level,
        event,
        extra={"event": event, **fields},
        stacklevel=2,
    )


def log_critical_error(event: str, error_type: str | None = None, **fields: Any) -> None:
    log_event(
        logging.ERROR,
        event,
        error_type=error_type or "Exception",
        **fields,
    )


def _safe_label(value: Any, default: str) -> str:
    text_value = str(value).strip() if value is not None else ""
    if not text_value or not _SAFE_LABEL_PATTERN.fullmatch(text_value):
        return default
    return text_value


def normalize_route(route: Any) -> str:
    if not isinstance(route, str) or not route:
        return "unmatched"
    normalized = re.sub(r"\{[^{}]+\}", "{}", route)
    normalized = re.sub(
        r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)",
        "/{}",
        normalized,
    )
    return _safe_label(normalized, "unmatched")


def _bucket_labels(duration_ms: float) -> dict[str, int]:
    buckets = {f"le_{int(bucket)}": int(duration_ms <= bucket) for bucket in _DURATION_BUCKETS_MS}
    buckets["le_inf"] = 1
    return buckets


@dataclass
class DurationMetric:
    count: int = 0
    sum_ms: float = 0.0
    buckets: dict[str, int] = field(default_factory=dict)


LabelTuple = tuple[tuple[str, str], ...]


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, LabelTuple], int] = defaultdict(int)
        self._durations: dict[tuple[str, LabelTuple], DurationMetric] = {}

    def _increment(self, name: str, labels: LabelTuple, amount: int = 1) -> None:
        self._counters[(name, labels)] += amount

    def _record_duration(self, name: str, labels: LabelTuple, duration_ms: float) -> None:
        metric = self._durations.setdefault((name, labels), DurationMetric())
        metric.count += 1
        metric.sum_ms += max(0.0, float(duration_ms))
        for bucket, value in _bucket_labels(duration_ms).items():
            metric.buckets[bucket] = metric.buckets.get(bucket, 0) + value

    def record_http(self, method: Any, route: Any, status_code: int, duration_ms: float) -> None:
        normalized_method = str(method).upper() if method is not None else ""
        method_label = normalized_method if normalized_method in _HTTP_METHODS else "OTHER"
        normalized_status = int(status_code) if isinstance(status_code, int) else 0
        status_class = f"{normalized_status // 100}xx" if 100 <= normalized_status <= 599 else "unknown"
        labels: LabelTuple = (
            ("method", method_label),
            ("route", normalize_route(route)),
            ("status_class", status_class),
        )
        with self._lock:
            self._increment("http_requests_total", labels)
            self._record_duration("http_request_duration_ms", labels, duration_ms)

    def record_evaluation(
        self,
        control_id: Any,
        result_status: Any,
        outcome: Any,
        duration_ms: float,
    ) -> None:
        control = str(control_id).upper() if control_id is not None else ""
        status = str(result_status).upper() if result_status is not None else "NONE"
        result_outcome = str(outcome).upper() if outcome is not None else "OTHER"
        labels: LabelTuple = (
            ("control", control if control in _CONTROL_IDS else "OTHER"),
            ("result", status if status in _RESULT_STATUSES else "NONE"),
            ("outcome", result_outcome if result_outcome in _OUTCOMES else "OTHER"),
        )
        with self._lock:
            self._increment("evaluations_total", labels)
            self._record_duration("evaluation_duration_ms", labels, duration_ms)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = [
                {"name": name, "labels": dict(labels), "value": value}
                for (name, labels), value in sorted(
                    self._counters.items(),
                    key=lambda item: (item[0][0], item[0][1]),
                )
            ]
            histograms = [
                {
                    "name": name,
                    "labels": dict(labels),
                    "count": metric.count,
                    "sum_ms": round(metric.sum_ms, 3),
                    "buckets": dict(sorted(metric.buckets.items())),
                }
                for (name, labels), metric in sorted(
                    self._durations.items(),
                    key=lambda item: (item[0][0], item[0][1]),
                )
            ]
        return {
            "service": SERVICE_NAME,
            "generated_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "counters": counters,
            "histograms": histograms,
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._durations.clear()


metrics = MetricsRegistry()


def get_metrics_snapshot() -> dict[str, Any]:
    return metrics.snapshot()


def reset_metrics() -> None:
    metrics.reset()


def _route_from_request(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return normalize_route(route_path)


def _record_http_request(
    request: Request,
    status_code: int,
    duration_ms: float,
    error_type: str | None,
) -> None:
    route = _route_from_request(request)
    method = str(request.method).upper()
    metrics.record_http(method, route, status_code, duration_ms)
    is_failure = status_code >= 500
    log_event(
        logging.ERROR if is_failure else logging.INFO,
        "http.request.failed" if is_failure else "http.request",
        method=method,
        route=route,
        status_code=status_code,
        duration_ms=duration_ms,
        error_type=error_type,
    )


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = bind_request_id(request_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as error:
                _record_http_request(
                    request,
                    500,
                    (time.perf_counter() - started) * 1000,
                    type(error).__name__,
                )
                raise
            response.headers[REQUEST_ID_HEADER] = request_id
            _record_http_request(request, response.status_code, (time.perf_counter() - started) * 1000, None)
            return response
        finally:
            reset_request_id(token)


def configuration_is_ready() -> bool:
    try:
        validate_environment()
    except ConfigurationError as error:
        log_critical_error("configuration.readiness.failed", error_type=type(error).__name__)
        return False
    return True


def database_is_ready(engine_factory: Callable[[], Engine], timeout_ms: int = READINESS_TIMEOUT_MS) -> bool:
    try:
        engine = engine_factory()
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text("SET LOCAL statement_timeout = :timeout"),
                    {"timeout": f"{int(timeout_ms)}ms"},
                )
            connection.execute(text("SELECT 1")).scalar_one()
    except (OSError, RuntimeError, SQLAlchemyError, ValueError) as error:
        log_critical_error("database.readiness.failed", error_type=type(error).__name__)
        return False
    return True


def readiness_status(engine_factory: Callable[[], Engine]) -> tuple[bool, str]:
    if not configuration_is_ready():
        return False, "configuration_invalid"
    if not database_is_ready(engine_factory):
        return False, "database_unavailable"
    return True, "ok"
