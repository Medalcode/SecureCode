# Dockerfile para SecureCode
# Optimizado para Cloud Run, Railway, Render y Docker Compose
FROM python:3.11-slim as runtime

# Variables de entorno de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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
