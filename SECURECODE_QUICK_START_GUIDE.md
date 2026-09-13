# SECURECODE — Quick Start Guide para Desarrolladores

**Objetivo:** Setup local completo en < 30 minutos  
**Audiencia:** Equipo de desarrollo (Jonatthan + Jose)  
**Requisitos:** Python 3.12, Docker, Git

---

## Paso 1: Clonar Repositorio (2 min)

```bash
git clone https://github.com/securecode/securecode.git
cd securecode

# Crear rama develop (base para feature branches)
git checkout -b develop
```

---

## Paso 2: Configurar Entorno Local (3 min)

### 2.1 Virtual Environment

```bash
# Crear venv
python3.12 -m venv venv

# Activar
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Verificar Python
python --version  # Debe ser 3.12.x
```

### 2.2 Variables de Entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar .env con valores locales
cat .env
```

**Contenido .env para desarrollo local:**

```env
# Base de datos (PostgreSQL local)
DATABASE_URL=postgresql://securecode_user:password123@localhost:5432/securecode_dev
DATABASE_POOL_SIZE=5
DATABASE_ECHO=true  # Ver SQL en console (dev only)

# GitHub
GITHUB_API_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Obtener token en https://github.com/settings/personal-access-tokens/new
# Permisos: repo (read-only)

# JWT Secrets (dev: cualquier valor ≥32 chars)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-dev-xxxxxxx
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24h
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# App
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG

# Admin usuario inicial (seed en DB)
ADMIN_EMAIL=admin@securecode.local
ADMIN_PASSWORD=admin123  # Será hasheado en DB seed
```

---

## Paso 3: Instalar Dependencias (5 min)

```bash
# Instalar requirements
pip install -r requirements.txt

# Instalar dev dependencies (pytest, black, flake8, etc)
pip install -r requirements-dev.txt

# Verificar instalación
pip list | grep -E "(FastAPI|SQLAlchemy|pytest)"
```

---

## Paso 4: Inicializar Base de Datos (5 min)

### 4.1 Crear DB PostgreSQL Local

```bash
# Opción A: Usando Docker Compose (recomendado)
docker-compose -f docker-compose.yml up -d

# Verificar que PostgreSQL está listo
docker-compose logs postgres
# Esperar mensaje "database system is ready to accept connections"

# Opción B: PostgreSQL local instalado
createdb securecode_dev -U securecode_user
```

### 4.2 Ejecutar Migraciones Alembic

```bash
# Crear tablas
alembic upgrade head

# Verificar schema
psql -U securecode_user -d securecode_dev -c "\dt"
# Debe listar: organizations, users, controls, rules, repositories, evidences, evaluations, audit_logs
```

### 4.3 Seed Admin Usuario

```bash
# Ejecutar script seed (crea admin@securecode.local / admin123)
python -c "from app.scripts.seed import seed_db; seed_db()"

# Verificar
psql -U securecode_user -d securecode_dev -c "SELECT email, role FROM users;"
```

---

## Paso 5: Ejecutar Aplicación Local (2 min)

```bash
# Terminal 1: API FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Debería ver:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete

# Verificar healthcheck
curl http://localhost:8000/healthcheck
# Response: {"status": "healthy", ...}
```

---

## Paso 6: Ejecutar Tests (5 min)

```bash
# Tests unitarios (debe pasar sin errores)
pytest tests/unit/ -v

# Tests integración
pytest tests/integration/ -v

# Cobertura
pytest tests/ --cov=app --cov-report=html
# Abrir htmlcov/index.html en browser

# Resultado esperado: Cobertura ≥85%
```

---

## Paso 7: Verificar Setup Completo (2 min)

### 7.1 Login y Obtener JWT

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@securecode.local",
    "password": "admin123"
  }'

# Response:
# {
#   "access_token": "eyJhbGc...",
#   "refresh_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 86400
# }

# Guardar token
export TOKEN="eyJhbGc..."
```

### 7.2 Crear Control de Prueba

```bash
curl -X POST http://localhost:8000/api/v1/controls \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "GH-001",
    "name": "Branch Protection",
    "description": "Test control",
    "severity": "HIGH"
  }'

# Response: {"id": "...", "code": "GH-001", ...}
```

### 7.3 Listar Controles

```bash
curl -X GET "http://localhost:8000/api/v1/controls?org_id=<org_id>" \
  -H "Authorization: Bearer $TOKEN"

# Response: {"items": [...], "total": 1}
```

---

## Paso 8: Configurar IDE (VS Code / PyCharm)

### VS Code

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ]
}
```

### PyCharm

1. Preferences → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Seleccionar `venv/bin/python`
4. Run → Edit Configurations
5. Add pytest configuration

---

## Paso 9: Workflow de Desarrollo Diario

### Estructura de Ramas (GitFlow)

```
main (producción)
  └─ v1.0.0 (tag)
  
develop (integración)
  └─ feature/GH-001-branch-protection (Jonatthan)
  └─ feature/github-connector-v2 (Jose)
  └─ feature/ground-truth-validation (Ambos)

hotfix/jwt-expiration-fix (si falla en prod)
```

### Commiting Cambios

```bash
# Crear rama feature
git checkout -b feature/GH-001-branch-protection

# Editar código, agregar tests

# Lint + Format antes de commit
black app tests
flake8 app tests
pytest tests/

# Commit con Conventional Commits
git add .
git commit -m "feat(engine): add branch protection evaluation logic"

# Push a feature branch
git push origin feature/GH-001-branch-protection

# Crear Pull Request en GitHub
# → PR description → linked issues → run CI → 2 approvals → merge
```

---

## Paso 9: Configurar para Producción (OPCIONAL)

### Opción A: Railway (Desarrollo)
```bash
# Para testing rápido (pero costo $5-10/mes)
# Seguir: https://docs.railway.app
```

### Opción B: Supabase + Cloud Run (RECOMENDADO - $0)

**Este es el método recomendado para MVP académico.**

```bash
# 1. Crear cuenta Supabase (1 min)
# https://app.supabase.com/

# 2. Crear proyecto:
#    - Name: securecode-mvp
#    - Region: us-east-1
#    - Plan: Free (IMPORTANTE)

# 3. Obtener connection string:
# Settings → Database → Connection String
# Copiar formato: postgresql://postgres:PASSWORD@db.REGION.supabase.co:5432/postgres

# 4. Actualizar .env
DATABASE_URL=postgresql://postgres:PASSWORD@db.us-east-1.supabase.co:5432/postgres

# 5. Test local contra Supabase
pytest tests/unit/ -v

# 6. Deploy a Cloud Run:
# Seguir: DEPLOYMENT_SUPABASE_CLOUD_RUN.md
```

**Costo: $0** (vs Railway $5-10/mes)  
**Tiempo: 30 minutos**  
**Para más detalles: Ver DEPLOYMENT_SUPABASE_CLOUD_RUN.md**

---

## Paso 10: Troubleshooting

### PostgreSQL no conecta (Desarrollo Local)

```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps

# Si no está up:
docker-compose up -d postgres

# Ver logs
docker-compose logs postgres

# Reconectar
psql -U securecode_user -d securecode_dev -c "SELECT 1"
```

### Supabase connection string inválido (Producción)

```bash
# Verificar en Supabase console:
# Settings → Database → Show Password
# Copiar exactamente (incluyendo caracteres especiales)

# En .env:
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.REGION.supabase.co:5432/postgres

# Test:
python -c "import sqlalchemy; print(sqlalchemy.create_engine('$DATABASE_URL'))"
```

### JWT token expirado en Postman

```bash
# Refrescar token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"

# Actualizar variable Postman
# Postman → Tests tab → set refreshed token
```

### Tests fallan con "no such table"

```bash
# Alembic migraciones no ejecutadas
alembic upgrade head

# Verificar
alembic current  # Debe mostrar última versión
```

### Puertos en uso

```bash
# Si puerto 8000 ocupado:
lsof -i :8000  # Listar procesos
kill -9 <PID>  # Matar proceso

# O usar puerto diferente
uvicorn app.main:app --port 8001
```

---

## Recursos Clave

| Recurso | URL |
|---------|-----|
| FastAPI Docs (Swagger) | http://localhost:8000/docs |
| FastAPI ReDoc | http://localhost:8000/redoc |
| Alembic Migrations | `db/alembic/versions/` |
| Tests Unitarios | `tests/unit/` |
| Tests Integración | `tests/integration/` |
| Ground Truth Dataset | `tests/fixtures/ground_truth_dataset.csv` |

---

## Checklist de Setup

- [ ] Repo clonado
- [ ] Venv creado y activado
- [ ] .env configurado
- [ ] Dependencies instaladas
- [ ] PostgreSQL corriendo (docker-compose up)
- [ ] Alembic upgrade head ejecutado
- [ ] Tests pasan (pytest tests/ -v)
- [ ] App inicia sin errores (uvicorn)
- [ ] Healthcheck responde 200
- [ ] Login retorna JWT válido
- [ ] Crear control exitoso
- [ ] IDE configurado (VS Code o PyCharm)

---

## Siguientes Pasos

1. **Jonatthan:** Implementar motor de reglas (app/domain/engine/evaluator.py)
2. **Jose:** Implementar conector GitHub (app/adapters/github/client.py)
3. **Ambos:** Implementar persistencia (app/adapters/persistence/)
4. **Ambos:** Escribir tests (tests/unit/, tests/integration/)
5. **Ambos:** Ejecutar Ground Truth validation

---

**¡Listo! El setup local está completo y la aplicación está lista para desarrollo.**

