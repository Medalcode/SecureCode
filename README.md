# SecureCode

Plataforma GRC (*Governance, Risk, and Compliance*) para la evaluación continua y automatizada de controles de seguridad en repositorios de código fuente (SCM).

Desarrollada mediante metodología **SDD (Specification-Driven Development)**, arquitectura hexagonal y principios FinOps.

---

## Capacidades Implementadas

- **GH-001 (Branch Protection Required Approvals & Stale Dismissal)**: Motor de evaluación determinista con umbrales estrictos de aprobación por pares y descarte de aprobaciones obsoletas.
- **GH-002 (Default Branch Protection Enabled)**: Motor de evaluación determinista que valida si la rama principal del repositorio se encuentra protegida contra sobreescrituras directas.
- **GH-003 (Signed Commits Required)**: Motor de evaluación determinista que verifica si la rama auditada exige commits firmados.
- **Adaptadores GitHub REST API**: Adquisición y normalización de evidencia en tiempo real con degradación elegante ante estados no observables (*tri-state*: `PASS`, `FAIL`, `UNKNOWN`).
- **Persistencia Inmutable en PostgreSQL**: Almacenamiento auditable con trazabilidad criptográfica (hashing canónico SHA-256 de evidencia cruda), integridad referencial estricta y migraciones versionadas con Alembic.
- **Autenticación y Seguridad**: Hashing de contraseñas con Argon2id, tokens de acceso JWT (HS256) con expiración configurable, validación de usuarios activos, vinculación de auditoría `requested_by_user_id`, CORS de lista permitida y cabeceras de seguridad para navegador.
- **Autorización y Auditoría**: Roles persistidos `admin` y `auditor`; los auditores requieren una autorización activa por repositorio (normalizada como `owner/repo`) y sólo acceden a su propio historial. Los administradores conservan el acceso operativo de plataforma y registran cada cambio de alcance.
- **Frontend SPA Minimalista (Estilo Gemini/ChatGPT)**: Interfaz web oscura/clara sin dependencias pesadas, con selector de controles, visor de evidencia en tiempo real, copia de hash SHA-256, telemetría del sistema, simulación en Sandbox y panel FinOps.
- **Contenedorización para Producción**: `Dockerfile` multi-stage basado en `python:3.11-slim`, sin compilador en runtime, con usuario no privilegiado (`appuser`, UID 10001); Compose ejecuta la API con filesystem de sólo lectura, sin capacidades Linux y sin escalamiento de privilegios.

---

## Métricas de Calidad y Verificación

- **Suite de Pruebas**: la cifra vigente se obtiene exclusivamente ejecutando `pytest -q`; no se publica un total fijo en el README porque evoluciona con cada control y migración.
- **Cobertura de Código**: se mide en CI con `pytest-cov`; consulte el artefacto de la ejecución vigente, no una cifra histórica.
- **Rendimiento de Carga (Locust)**: la evidencia ES2 es una medición controlada histórica con mock local. Debe repetirse con el flujo actual de GitHub antes de usarse como capacidad de producción.

---

## Ejecución Rápida

### Opción 1: Docker Compose — Entorno Local

> [!IMPORTANT]
> Docker Compose requiere que las variables de entorno estén configuradas **antes** de iniciar los contenedores. El archivo `docker-compose.yml` **no contiene credenciales** y fallará explícitamente si alguna variable obligatoria falta.

```bash
# 1. Clonar repositorio
git clone https://github.com/Medalcode/SecureCode.git
cd SecureCode

# 2. Crear archivo .env a partir de la plantilla
cp .env.example .env
# Editar .env con tus valores reales (nunca commitear .env)

# 3. Iniciar servicios
docker compose up --build -d

# 4. Aplicar migraciones de base de datos (ver sección Alembic más abajo)
docker compose exec api alembic upgrade head

# 5. Crear usuario inicial (sin contraseña en CLI)
docker compose exec api sh -c "SEED_USER_EMAIL=auditor@empresa.com SEED_USER_PASSWORD=<contraseña_segura> python scripts/seed_user.py"
```

> El primer usuario puede inicializarse con `SEED_USER_ROLE=admin`. Las cuentas existentes pasan a `auditor` tras ejecutar la migración de roles, aplicando mínimo privilegio. Cree administradores adicionales sólo mediante una sesión administrativa autorizada.

Acceder: **`http://localhost:8000/`** | Swagger: **`http://localhost:8000/docs`**

---

### Opción 2: Entorno Local Python

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate          # Linux/macOS

pip install -e .

# Configurar variables mínimas
cp .env.example .env
# Editar .env: DATABASE_URL, JWT_SECRET_KEY

python -m uvicorn securecode.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## Migraciones de Base de Datos (Alembic)

> [!IMPORTANT]
> Las migraciones **nunca se ejecutan automáticamente** al arrancar el contenedor. Son una operación deliberada y separada del ciclo de vida del servicio.

**Propósito de la separación:**
- En entornos con múltiples réplicas (Cloud Run), ejecutar migraciones DDL al arranque puede provocar bloqueos (`AccessExclusiveLock`) si varias instancias intentan migrar simultáneamente.
- Desacoplar migraciones permite controlar exactamente cuándo y cómo se aplican los cambios de esquema.

### Aplicar migraciones — Local

```bash
# Con Docker Compose (base de datos 'db' debe estar arriba y sana)
docker compose exec api alembic upgrade head

# Sin Docker (requiere DATABASE_URL en entorno)
DATABASE_URL=postgresql://user:pass@host:5432/db alembic upgrade head
```

### Aplicar migraciones — Cloud Run Job (Producción)

```bash
# Crear el job de migración (sólo la primera vez)
gcloud run jobs create securecode-migrate \
  --image <REGION>-docker.pkg.dev/<PROJECT_ID>/securecode/securecode:latest \
  --command "alembic" \
  --args "upgrade,head" \
  --set-secrets "DATABASE_URL=securecode-db-url:latest" \
  --region us-central1

# Ejecutar migraciones (antes de cada despliegue con cambios de esquema)
gcloud run jobs execute securecode-migrate --wait --region us-central1
```

### Revertir esquema (rollback de base de datos)

> [!WARNING]
> El **rollback de aplicación** (redirigir tráfico a una revisión anterior de Cloud Run) y el **rollback de base de datos** (Alembic `downgrade`) son operaciones **independientes y distintas**.
> Revertir la aplicación **no** revierte automáticamente el esquema. Si el nuevo esquema es incompatible con la versión anterior de la aplicación, se deben coordinar ambos rollbacks explícitamente.

```bash
# Ver revisión actual en la base de datos
alembic current

# Revertir una versión
alembic downgrade -1

# Revertir a una revisión específica
alembic downgrade <revision_id>
```

---

## Guía de Despliegue Seguro en Google Cloud Run

### Lista de verificación antes de producción

- Definir `APP_ENV=production`, `CORS_ORIGINS` con los dominios HTTPS exactos y `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` según la política de sesión.
- Inyectar `DATABASE_URL`, `JWT_SECRET_KEY`, `GITHUB_TOKEN` y las credenciales del usuario inicial exclusivamente desde Secret Manager.
- Ejecutar `alembic upgrade head` como Job antes de transferir tráfico.
- Crear el usuario inicial con una contraseña única y conservar sólo el hash Argon2id; no existe acceso de demostración en producción.
- Confirmar `/health`, el inicio de sesión y una evaluación autenticada en la revisión candidata antes de mover tráfico.
- Configurar TLS, dominio y WAF/rate limiting en el balanceador o proveedor. La API aplica además un bloqueo persistente configurable tras intentos fallidos (`LOGIN_MAX_FAILURES=5`, `LOGIN_WINDOW_SECONDS=900`); el WAF sigue siendo necesario para limitar abuso por IP antes de consumir Argon2id.

La interfaz no acepta ni guarda PATs de GitHub. La credencial de integración se configura sólo en el entorno del servidor y debe tener permisos mínimos de lectura.

### Prerrequisitos

1. Base de datos PostgreSQL accesible desde Cloud Run (Supabase, Cloud SQL, Neon, etc.).
2. Migraciones aplicadas contra la base de datos de producción (ver sección anterior).
3. Secretos creados en Google Cloud Secret Manager.

### Paso 1: Crear secretos en Secret Manager

```bash
# JWT Secret (generar localmente, nunca compartir)
python -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets create securecode-jwt-secret --data-file=-

# Database URL (no incluir credenciales en el comando)
echo -n "postgresql://user:pass@host:6543/db?sslmode=require" | \
  gcloud secrets create securecode-db-url --data-file=-

# GitHub Token (PAT de grano fino, limitado a repositorios auditados, con Metadata: Read y Administration: Read)
echo -n "ghp_..." | \
  gcloud secrets create securecode-github-token --data-file=-
```

### Paso 2: Ejecutar migraciones antes del despliegue

```bash
gcloud run jobs execute securecode-migrate --wait --region us-central1
```

### Paso 3: Desplegar con `--set-secrets` (NO `--set-env-vars` para secretos)

```bash
gcloud run deploy securecode \
  --image <REGION>-docker.pkg.dev/<PROJECT_ID>/securecode/securecode:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "PORT=8000,LOG_LEVEL=INFO,JWT_ALGORITHM=HS256" \
  --set-secrets "DATABASE_URL=securecode-db-url:latest,JWT_SECRET_KEY=securecode-jwt-secret:latest,GITHUB_TOKEN=securecode-github-token:latest" \
  --no-traffic \
  --tag candidate
```

> [!CAUTION]
> Nunca uses `--set-env-vars` para pasar secretos. Las variables de entorno configuradas así son visibles en la consola de Cloud Run, en los metadatos del servicio y en Cloud Logging. Usa siempre `--set-secrets`.

### Paso 4: Transferir tráfico tras validar

```bash
# Verificar que la revisión candidata responde correctamente
curl https://candidate---securecode-<hash>-uc.a.run.app/health

# Transferir el 100% del tráfico
gcloud run services update-traffic securecode --to-latest --region us-central1
```

### Paso 5: Validación de la revisión candidata

Configure los secretos protegidos de GitHub `CANDIDATE_SMOKE_USERNAME` y `CANDIDATE_SMOKE_PASSWORD`. Luego ejecute manualmente el workflow **Candidate Deployment Smoke Test** e indique la URL HTTPS etiquetada como `candidate` de Cloud Run. El workflow verifica salud, cabeceras, inicio de sesión, identidad y acceso al historial; publica un artefacto JSON sin credenciales.

También puede ejecutarse desde un entorno controlado:

```bash
SECURECODE_CANDIDATE_URL=https://candidate.example.run.app \
SMOKE_USERNAME=auditor@empresa.com \
SMOKE_PASSWORD='<contraseña>' \
python scripts/verify_candidate.py
```

No transfiera tráfico hasta que este smoke test y la migración Alembic del candidato finalicen correctamente.

### Rollback de Aplicación (< 30 segundos)

```bash
# Listar revisiones disponibles
gcloud run revisions list --service securecode --region us-central1

# Redirigir todo el tráfico a la revisión anterior
gcloud run services update-traffic securecode \
  --to-revisions <REVISION_ANTERIOR>=100 \
  --region us-central1
```

---

## Arquitectura del Proyecto

```
SecureCode/
├── .github/workflows/       # CI/CD: Tests, E2E, Docker Smoke Test
├── alembic/                 # Migraciones de esquema PostgreSQL
├── docs/specs/              # Especificaciones SDD (GH-001, GH-002, DEPLOY-002)
├── docs/figures/            # Diagramas e imágenes del informe
├── rules/                   # Catálogo canónico de reglas JSON (GH-001, GH-002)
├── scripts/                 # Semillero de usuarios, Locust, benchmarks
├── src/securecode/
│   ├── adapters/            # Adaptadores externos (GitHub REST API, PostgreSQL)
│   ├── api/                 # Endpoints FastAPI, esquemas Pydantic y seguridad JWT
│   ├── application/         # Casos de uso (evaluate_and_store)
│   ├── engine/              # Motor determinista de evaluación de reglas
│   ├── models/              # Modelos canónicos de evidencia y reglas
│   ├── ports/               # Interfaces / Puertos de repositorio
│   └── static/              # Frontend SPA (HTML5, CSS, Vanilla JS)
├── tests/                   # Suite de pruebas unitarias, integración y seguridad
├── Dockerfile               # Contenedor de producción multi-stage
├── docker-compose.yml       # Orquestación local (requiere .env externo)
└── pyproject.toml           # Configuración del proyecto y dependencias
```

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulte el archivo LICENSE para más detalles.
