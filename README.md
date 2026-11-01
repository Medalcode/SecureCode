# SecureCode

Plataforma GRC (*Governance, Risk, and Compliance*) para la evaluación continua y automatizada de controles de seguridad en repositorios de código fuente (SCM).

Desarrollada mediante metodología **SDD (Specification-Driven Development)**, arquitectura hexagonal y principios FinOps.

---

## Capacidades Implementadas

- **GH-001 (Branch Protection Required Approvals & Stale Dismissal)**: Motor de evaluación determinista con umbrales estrictos de aprobación por pares y descarte de aprobaciones obsoletas.
- **GH-002 (Default Branch Protection Enabled)**: Motor de evaluación determinista que valida si la rama principal del repositorio se encuentra protegida contra sobreescrituras directas.
- **Adaptadores GitHub REST API**: Adquisición y normalización de evidencia en tiempo real con degradación elegante ante estados no observables (*tri-state*: `PASS`, `FAIL`, `UNKNOWN`).
- **Persistencia Inmutable en PostgreSQL**: Almacenamiento auditable con trazabilidad criptográfica (hashing canónico SHA-256 de evidencia cruda), integridad referencial estricta y migraciones versionadas con Alembic.
- **Autenticación y Seguridad**: Hashing de contraseñas con Argon2id, tokens de acceso JWT (HS256) con expiración configurable, vinculación de auditoría `requested_by_user_id` y rate limiting.
- **Frontend SPA Minimalista (Estilo Gemini/ChatGPT)**: Interfaz web oscura/clara (`color-scheme: light dark`) sin dependencias pesadas, con selector de controles, visor de evidencia en tiempo real, copia de hash SHA-256, telemetría del sistema, simulación en Sandbox y panel FinOps.
- **Contenedorización para Producción**: `Dockerfile` multi-stage ligero basado en `python:3.11-slim` con usuario no privilegiado (`appuser`, UID 10001) y orquestación completa con `docker-compose.yml`.

---

## Métricas de Calidad y Verificación

- **Suite de Pruebas**: 95/95 pruebas aprobadas (Unitarias, API REST, Seguridad JWT, Matriz de Estados GH-002 e Integración con PostgreSQL 15).
- **Cobertura de Código**: **89.5%** en CI (`pytest-cov`), con 100% de cobertura en modelos de dominio y 95% en evaluadores de reglas.
- **Rendimiento de Carga (Locust)**: Latencia nominal P95 de **180 ms** (P95 bajo estrés de **200 ms**, P98 de **300 ms**), tasa de rendimiento de **20.45 RPS** y **0.0%** de errores HTTP bajo concurrencia sostenida.
- **Ground Truth**: Exactitud, exhaustividad y precisión del **100%** validada frente a 10 repositorios sintéticos en el benchmark de referencia.

---

## Ejecución Rápida

### Opción 1: Docker Compose (Recomendado para Producción Local)

Levanta la base de datos PostgreSQL 15 y la API de SecureCode en contenedores aislados:

```bash
# 1. Clonar repositorio
git clone https://github.com/Medalcode/SecureCode.git
cd SecureCode

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Iniciar servicios en segundo plano
docker compose up --build -d

# 4. Aplicar migraciones en la base de datos
docker compose exec api alembic upgrade head

# 5. Sembrar usuario auditor inicial
docker compose exec api python scripts/seed_user.py auditor@empresa.com securecode2026!
```

Acceder a la aplicación web: **`http://localhost:8000/`**  
Documentación Swagger / OpenAPI: **`http://localhost:8000/docs`**

---

### Opción 2: Entorno Local de Desarrollo (Python)

```bash
# Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -e .

# Configurar variables mínimas en .env o entorno
# GITHUB_TOKEN=ghp_...
# JWT_SECRET_KEY=clave-secreta-de-al-menos-32-caracteres

# Iniciar servidor Uvicorn
python -m uvicorn securecode.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## Estructura de la Interfaz Web (SPA)

La interfaz web está montada de forma nativa en FastAPI (`/`) y ofrece:

1. **Dashboard de Evaluación**:
   - Selector interactivo de control (`GH-001` / `GH-002`).
   - Formulario de repositorio (`owner/repo`) y rama objetivo.
   - Tarjetas de resultado con badge de estado tri-state (`PASS` verde, `FAIL` rojo, `UNKNOWN` ámbar).
   - Huella digital criptográfica SHA-256 con botón de copiado en 1 clic para verificación de no repudio.
   - Visor JSON formateado de la evidencia cruda recolectada.
2. **Historial de Auditoría**: Línea temporal de ejecuciones recientes persistidas en base de datos.
3. **Simulador Sandbox**: Entorno de pruebas para simular escenarios de cumplimiento sin invocar la API de GitHub en vivo.
4. **Catálogo de Reglas**: Inspección de reglas canónicas JSON (`GH-001.json`, `GH-002.json`).
5. **Panel FinOps & Capacidad**: Indicadores de cuota mensual, proyección de almacenamiento (~25 KB/evaluación $\rightarrow$ 20,480 evaluaciones en tier Supabase 500 MB) y telemetría de latencias y SLAs.

---

## Guía de Despliegue en la Nube

### Despliegue en Google Cloud Run

1. **Compilar y publicar imagen en Artifact Registry**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/securecode:latest .
   ```
2. **Desplegar servicio**:
   ```bash
   gcloud run deploy securecode \
     --image gcr.io/PROJECT_ID/securecode:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars "DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db,JWT_SECRET_KEY=clave_secreta_segura,GITHUB_TOKEN=ghp_..."
   ```

### Despliegue en Railway / Render

1. Conectar el repositorio de GitHub al dashboard de Railway o Render.
2. Añadir un plugin / servicio de PostgreSQL gestionado.
3. Configurar las variables de entorno en el panel de configuración:
   - `DATABASE_URL`: Vinculada automáticamente al servicio PostgreSQL.
   - `JWT_SECRET_KEY`: String de 32+ caracteres aleatorios.
   - `GITHUB_TOKEN`: Personal Access Token con permisos de lectura (`read:org`, `repo`).
   - `PORT`: `8000`
4. Ejecutar el comando de release: `alembic upgrade head && python scripts/seed_user.py auditor@empresa.com securecode2026!`

---

## Arquitectura del Proyecto

```
SecureCode/
├── .github/workflows/       # CI/CD: Tests, E2E, Docker Smoke Test
├── alembic/                 # Migraciones de esquema PostgreSQL
├── docs/                    # Especificaciones SDD, diagramas C4 y evidencias
├── rules/                   # Catálogo canónico de reglas JSON (GH-001, GH-002)
├── scripts/                 # Semillero de usuarios, suite de carga Locust, benchmarks
├── src/securecode/
│   ├── adapters/            # Adaptadores externos (GitHub REST API, PostgreSQL)
│   ├── api/                 # Endpoints FastAPI, esquemas Pydantic y seguridad JWT
│   ├── application/         # Casos de uso de negocio (evaluate_and_store)
│   ├── engine/              # Motor determinista de evaluación de reglas
│   ├── models/              # Modelos canónicos de evidencia y reglas
│   ├── ports/               # Interfaces / Puertos de repositorio y auditoría
│   └── static/              # Frontend SPA (HTML5, CSS moderno, Vanilla JS)
├── tests/                   # Suite de pruebas unitarias, de integración y de seguridad
├── Dockerfile               # Contenedor de producción multi-stage
├── docker-compose.yml       # Orquestación de desarrollo y producción local
└── pyproject.toml           # Configuración del proyecto y dependencias
```

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulte el archivo LICENSE para más detalles.
