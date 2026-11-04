# Dockerfile para SecureCode
# Build separado: las herramientas de compilación no llegan a la imagen final.
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /build/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime

# Variables de entorno de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    PORT=8000

WORKDIR /app

# Sólo librerías de ejecución y curl para el healthcheck. gcc/libpq-dev quedan en builder.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copiar el código fuente y artefactos del proyecto
COPY src/ /app/src/
COPY rules/ /app/rules/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/
COPY pyproject.toml /app/

# Crear usuario sin privilegios por seguridad (NIST / OWASP)
RUN useradd -m -u 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Verificación de salud integrada
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando de arranque con soporte para puerto dinámico de Cloud Run
CMD ["sh", "-c", "uvicorn securecode.api.app:app --host 0.0.0.0 --port ${PORT}"]
