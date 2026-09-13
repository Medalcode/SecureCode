# SECURECODE — Anexos Completos (ES2)

**Documento:** Anexos A1–A10 del Informe ES2  
**Versión:** 2.0  
**Fecha:** 31 de agosto de 2026

---

## ANEXO 1: Diccionario de Datos Completo (DDL PostgreSQL)

### Schema Relacional (8 Tablas, 44 Campos)

```sql
-- ==================================================
-- ANEXO 1: DICCIONARIO DE DATOS COMPLETO
-- ==================================================

-- ==================== ORGANIZATIONS ====================
-- Tabla: organizations (Raíz de multi-tenancy ready)

| Campo        | Tipo          | Constraints              | Descripción                          |
|--------------|---------------|--------------------------|--------------------------------------|
| id           | UUID          | PRIMARY KEY, DEFAULT     | ID único organización                |
| name         | VARCHAR(255)  | NOT NULL, UNIQUE         | Nombre descriptivo                   |
| created_at   | TIMESTAMP     | NOT NULL, DEFAULT NOW()  | Timestamp creación                   |

-- Índices
CREATE INDEX idx_organizations_name ON organizations(name);

-- ==================== USERS ====================
-- Tabla: users (Administradores por organización)

| Campo           | Tipo          | Constraints                      | Descripción                |
|-----------------|---------------|----------------------------------|----------------------------|
| id              | UUID          | PRIMARY KEY, DEFAULT             | ID único usuario           |
| org_id          | UUID          | NOT NULL, FK organizations(id)   | Relación organización      |
| email           | VARCHAR(255)  | NOT NULL, UNIQUE                 | Email login (único global) |
| password_hash   | VARCHAR(255)  | NOT NULL                         | Hash Argon2 (NUNCA plain)  |
| role            | VARCHAR(20)   | NOT NULL, CHECK admin/analyst... | Rol de usuario             |
| is_active       | BOOLEAN       | DEFAULT true                     | Soft-delete flag           |
| created_at      | TIMESTAMP     | NOT NULL, DEFAULT NOW()          | Timestamp creación         |
| updated_at      | TIMESTAMP     | NOT NULL, DEFAULT NOW()          | Timestamp último cambio    |

-- Índices
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ==================== CONTROLS ====================
-- Tabla: controls (Requisitos de seguridad)

| Campo        | Tipo          | Constraints                  | Descripción                |
|--------------|---------------|------------------------------|----------------------------|
| id           | UUID          | PRIMARY KEY, DEFAULT         | ID único control           |
| org_id       | UUID          | NOT NULL, FK organizations   | Relación organización      |
| code         | VARCHAR(50)   | NOT NULL                     | Ej: "GH-001" (único org)   |
| name         | VARCHAR(255)  | NOT NULL                     | Nombre descriptivo         |
| description  | TEXT          | NULLABLE                     | Descripción extendida      |
| framework    | VARCHAR(100)  | NULLABLE                     | Ej: "NIST-800-53"          |
| severity     | VARCHAR(20)   | CHECK CRITICAL/HIGH/MEDIUM   | Nivel de importancia       |
| version      | INTEGER       | DEFAULT 1                    | Versionamiento control     |
| created_at   | TIMESTAMP     | NOT NULL, DEFAULT NOW()      | Timestamp creación         |
| updated_at   | TIMESTAMP     | NOT NULL, DEFAULT NOW()      | Timestamp último cambio    |

-- Constraints
UNIQUE(org_id, code)  -- Code único por organización

-- Índices
CREATE INDEX idx_controls_org_id ON controls(org_id);
CREATE INDEX idx_controls_framework ON controls(framework);
CREATE INDEX idx_controls_severity ON controls(severity);

-- ==================== RULES ====================
-- Tabla: rules (Expresiones declarativas de evaluación)

| Campo           | Tipo          | Constraints                     | Descripción                    |
|-----------------|---------------|----------------------------------|--------------------------------|
| id              | UUID          | PRIMARY KEY, DEFAULT            | ID única regla                 |
| control_id      | UUID          | NOT NULL, FK controls(id)       | Relación control               |
| expression_json | JSONB         | NOT NULL                        | Expresión: {operator, left, righ} |
| version         | INTEGER       | NOT NULL, DEFAULT 1             | Versionamiento regla           |
| is_active       | BOOLEAN       | NOT NULL, DEFAULT true          | Soft-delete flag               |
| created_at      | TIMESTAMP     | NOT NULL, DEFAULT NOW()         | Timestamp creación             |
| updated_at      | TIMESTAMP     | NOT NULL, DEFAULT NOW()         | Timestamp último cambio        |

-- Índices
CREATE INDEX idx_rules_control_id ON rules(control_id);
CREATE INDEX idx_rules_is_active ON rules(is_active);
CREATE INDEX idx_rules_version ON rules(version);

-- ==================== REPOSITORIES ====================
-- Tabla: repositories (Fuentes a evaluar)

| Campo     | Tipo          | Constraints                   | Descripción                 |
|-----------|---------------|-------------------------------|-----------------------------|
| id        | UUID          | PRIMARY KEY, DEFAULT          | ID repositorio              |
| org_id    | UUID          | NOT NULL, FK organizations    | Relación organización       |
| name      | VARCHAR(255)  | NOT NULL                      | Nombre repo (ej: my-app)   |
| owner     | VARCHAR(255)  | NOT NULL                      | Owner GitHub (org o user)   |
| url       | VARCHAR(255)  | NOT NULL, UNIQUE              | URL https://github.com/...  |
| created_at| TIMESTAMP     | NOT NULL, DEFAULT NOW()       | Timestamp creación          |

-- Constraints
UNIQUE(org_id, owner, name)  -- Repo único por org

-- Índices
CREATE INDEX idx_repositories_org_id ON repositories(org_id);
CREATE INDEX idx_repositories_url ON repositories(url);

-- ==================== EVIDENCES ====================
-- Tabla: evidences (Datos normalizados de fuentes)

| Campo          | Tipo          | Constraints                    | Descripción                    |
|----------------|---------------|--------------------------------|--------------------------------|
| id             | UUID          | PRIMARY KEY, DEFAULT           | ID evidencia                   |
| repository_id  | UUID          | NOT NULL, FK repositories(id)  | Relación repositorio           |
| payload        | JSONB         | NOT NULL                       | Datos normalizados             |
| hash_sha256    | CHAR(64)      | NOT NULL                       | SHA-256 fingerprint            |
| source         | VARCHAR(40)   | NOT NULL, DEFAULT 'github'     | Tipo fuente (github/aws/etc)   |
| created_at     | TIMESTAMP     | NOT NULL, DEFAULT NOW()        | Timestamp recolección          |

-- Índices
CREATE INDEX idx_evidences_repository_id ON evidences(repository_id);
CREATE INDEX idx_evidences_hash_sha256 ON evidences(hash_sha256);
CREATE INDEX idx_evidences_created_at ON evidences(created_at);
CREATE INDEX idx_evidences_source ON evidences(source);

-- ==================== EVALUATIONS ====================
-- Tabla: evaluations (Resultados de evaluación — INMUTABLE)

| Campo                 | Tipo          | Constraints                    | Descripción                    |
|-----------------------|---------------|--------------------------------|--------------------------------|
| id                    | UUID          | PRIMARY KEY, DEFAULT           | ID evaluación                  |
| rule_id               | UUID          | NOT NULL, FK rules(id)         | Relación regla                 |
| evidence_id           | UUID          | NULLABLE, FK evidences(id)     | NULL si UNKNOWN                |
| status                | VARCHAR(20)   | NOT NULL, ENUM PASS/FAIL/UNK   | Resultado evaluación           |
| evaluated_at          | TIMESTAMP     | NOT NULL, DEFAULT NOW()        | Timestamp evaluación           |
| evidence_hash_at_time | CHAR(64)      | NOT NULL                       | Hash evidencia en momento eval |

-- Constraints
CHECK (status IN ('PASS', 'FAIL', 'UNKNOWN'))
CHECK ((status = 'UNKNOWN' AND evidence_id IS NULL) OR (status IN ('PASS', 'FAIL') AND evidence_id IS NOT NULL))

-- Índices
CREATE INDEX idx_evaluations_rule_id ON evaluations(rule_id);
CREATE INDEX idx_evaluations_evidence_id ON evaluations(evidence_id);
CREATE INDEX idx_evaluations_status ON evaluations(status);
CREATE INDEX idx_evaluations_evaluated_at ON evaluations(evaluated_at);

-- ==================== AUDIT_LOGS ====================
-- Tabla: audit_logs (Trazabilidad de acciones)

| Campo      | Tipo          | Constraints                   | Descripción                    |
|------------|---------------|-------------------------------|-----------------------------|
| id         | BIGSERIAL     | PRIMARY KEY                   | ID log (secuencial)            |
| org_id     | UUID          | NOT NULL, FK organizations    | Relación organización          |
| user_id    | UUID          | NULLABLE, FK users(id)        | Usuario si autenticado         |
| action     | VARCHAR(50)   | NOT NULL                      | Tipo acción (LOGIN, etc)       |
| details    | JSONB         | NULLABLE                      | Contexto adicional             |
| created_at | TIMESTAMP     | NOT NULL, DEFAULT NOW()       | Timestamp acción               |

-- Índices
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## ANEXO 2: Especificación Detallada de Casos de Uso

### CU-01: Autenticar Usuario

**Actor Principal:** Administrador  
**Precondiciones:**
- Usuario existe en BD con email y password_hash válidos
- Aplicación está disponible

**Flujo Principal:**
1. Usuario ingresa email y password
2. Sistema valida credenciales (Argon2 verify)
3. Sistema genera JWT access token (TTL 24h) + refresh token (TTL 7d)
4. Sistema retorna tokens

**Flujo Alternativo (Credenciales Inválidas):**
1. Usuario ingresa email/password incorrecto
2. Sistema retorna error 401 "Invalid credentials"
3. Sistema registra intento fallido en audit_logs

**Postcondiciones:**
- Usuario autenticado tiene access_token válido
- Token vinculado a email específico

---

### CU-02: Conectar Repositorio GitHub

**Actor Principal:** Administrador  
**Precondiciones:**
- Usuario autenticado (tiene JWT válido)
- Repositorio existe en GitHub
- Token GitHub tiene permisos de lectura

**Flujo Principal:**
1. Admin ingresa owner y nombre repositorio
2. Sistema valida contra GitHub API (GET /repos/{owner}/{repo})
3. Sistema persiste repositorio en tabla repositories
4. Sistema retorna confirmación

**Flujo Alternativo (Repo No Existe):**
1. GitHub retorna 404
2. Sistema retorna error "Repository not found"

**Flujo Alternativo (Permisos Insuficientes):**
1. GitHub retorna 403 Forbidden
2. Sistema retorna error "Access denied to repository"

---

### CU-03: Ejecutar Evaluación

**Actor Principal:** Administrador o Sistema (scheduler)  
**Precondiciones:**
- Regla existe y está activa (is_active = true)
- Repositorio conectado
- Evidencia disponible (o se ingesta automáticamente)

**Flujo Principal:**
1. Sistema obtiene regla del catálogo
2. Sistema obtiene evidencia más reciente del repositorio
3. Motor evalúa regla contra evidencia → PASS | FAIL | UNKNOWN
4. Sistema persiste resultado en evaluations (inmutable)
5. Sistema retorna resultado

**Flujo Alternativo (Sin Evidencia):**
1. Sistema no encuentra evidencia reciente
2. Motor clasifica como UNKNOWN
3. Registra evidence_id = NULL

**Postcondiciones:**
- Resultado persistido e inmutable
- Auditable con hash de evidencia al momento de evaluación

---

### CU-04: Gestionar Catálogo (CRUD)

**Actor Principal:** Administrador  

**Crear Control (CREATE):**
- POST /api/v1/controls
- Ingresa: code, name, description, framework, severity
- Sistema genera UUID, timestamp
- Retorna control creado

**Leer Controles (READ):**
- GET /api/v1/controls?org_id=...
- Sistema retorna lista paginada

**Actualizar Control (UPDATE):**
- PUT /api/v1/controls/{id}
- Solo campos: name, description, severity
- Code no mutable (es clave de negocio)
- Sistema actualiza updated_at

**Eliminar Control (DELETE):**
- DELETE /api/v1/controls/{id}
- Soft-delete: marcas is_active = false
- No elimina historial de evaluaciones

---

### CU-05: Consultar Reporte

**Actor Principal:** Administrador  
**Precondiciones:**
- Usuario autenticado
- Existen evaluaciones en BD

**Flujo Principal:**
1. Admin solicita reporte de control específico
2. Sistema consolida evaluaciones por control
3. Calcula estadísticas:
   - Cantidad PASS, FAIL, UNKNOWN
   - Porcentaje cumplimiento = PASS / (PASS + FAIL) × 100
   - Confianza = (PASS + FAIL) / Total × 100
4. Sistema retorna reporte tabular con breakdown por repositorio

**Formato Reporte:**
```json
{
  "control_id": "...",
  "control_name": "Branch Protection Required",
  "total_evaluations": 10,
  "pass_count": 8,
  "fail_count": 1,
  "unknown_count": 1,
  "compliance_percentage": 88.9,
  "confidence_percentage": 90.0,
  "repositories": [
    {
      "name": "repo-1",
      "status": "PASS",
      "evaluated_at": "2026-09-01T10:35:00Z"
    },
    ...
  ]
}
```

---

### CU-06: Exportar JSON

**Actor Principal:** Administrador  
**Precondiciones:**
- Usuario autenticado
- Reporte generado

**Flujo Principal:**
1. Admin solicita export a JSON
2. Sistema serializa reporte completo
3. Sistema calcula HMAC-SHA256(reporte_json, secret_key)
4. Sistema retorna JSON con header `X-Report-Signature`

**Seguridad:**
- Cliente puede verificar que reporte no fue modificado post-descarga
- Firma = HMAC-SHA256(report_json, JWT_SECRET_KEY)

---

### CU-07: Verificar Hash Integridad

**Actor Principal:** Sistema  
**Disparador:** Automático durante evaluación

**Flujo Principal:**
1. Motor recibe evidencia
2. Calcula SHA-256 de payload canónico
3. Compara con hash_sha256 almacenado en BD
4. Si coincide → evidencia íntegra, evaluar
5. Si no coincide → UNKNOWN (posible corrupción)

**Auditoría:**
- Cada evaluación almacena evidence_hash_at_time
- Permite detectar cambios de evidencia post-evaluación

---

## ANEXO 3: Catálogo de Controles y Reglas (MVP)

### Control 1: Branch Protection Habilitado

```json
{
  "control": {
    "code": "GH-001",
    "name": "Branch Protection Requerido",
    "description": "El repositorio debe tener protección de rama habilitada en main/master",
    "framework": "NIST-800-53",
    "severity": "HIGH"
  },
  "rules": [
    {
      "id": "rule-001-01",
      "version": 1,
      "is_active": true,
      "expression": {
        "operator": "==",
        "left": "branch_protection_enabled",
        "right": true
      },
      "description": "Branch protection debe estar explícitamente habilitado"
    }
  ]
}
```

### Control 2: Pull Request Reviews Requeridas

```json
{
  "control": {
    "code": "GH-002",
    "name": "Pull Request Reviews Requeridas",
    "description": "Mínimo 2 reviews de código antes de merge",
    "framework": "NIST-800-53",
    "severity": "HIGH"
  },
  "rules": [
    {
      "id": "rule-002-01",
      "version": 1,
      "is_active": true,
      "expression": {
        "operator": ">=",
        "left": "required_reviews",
        "right": 2
      },
      "description": "Required reviews debe ser ≥2"
    },
    {
      "id": "rule-002-02",
      "version": 1,
      "is_active": true,
      "expression": {
        "operator": "AND",
        "left": {
          "operator": ">=",
          "left": "required_reviews",
          "right": 2
        },
        "right": {
          "operator": "==",
          "left": "dismiss_stale_reviews",
          "right": true
        }
      },
      "description": "2+ reviews + dismiss stale reviews"
    }
  ]
}
```

### Control 3: Code Owner Review Requerida

```json
{
  "control": {
    "code": "GH-003",
    "name": "Code Owner Review Obligatorio",
    "description": "Cambios en archivos críticos requieren aprobación del code owner",
    "framework": "NIST-800-53",
    "severity": "CRITICAL"
  },
  "rules": [
    {
      "id": "rule-003-01",
      "version": 1,
      "is_active": true,
      "expression": {
        "operator": "==",
        "left": "code_owner_review_required",
        "right": true
      },
      "description": "Code owner review must be required"
    }
  ]
}
```

---

## ANEXO 4: Dataset Ground Truth (100 Casos)

```csv
evidence_id,control_code,normalized_payload,expected_status,rule_id
pass_001,GH-001,"{""branch_protection_enabled"": true}",PASS,rule-001-01
pass_002,GH-001,"{""branch_protection_enabled"": true, ""required_reviews"": 2}",PASS,rule-001-01
pass_003,GH-002,"{""required_reviews"": 2}",PASS,rule-002-01
pass_004,GH-002,"{""required_reviews"": 2, ""dismiss_stale_reviews"": true}",PASS,rule-002-02
pass_005,GH-002,"{""required_reviews"": 3, ""dismiss_stale_reviews"": true}",PASS,rule-002-02
pass_006,GH-002,"{""required_reviews"": 3}",PASS,rule-002-01
pass_007,GH-003,"{""code_owner_review_required"": true}",PASS,rule-003-01
pass_008,GH-001,"{""branch_protection_enabled"": true, ""force_push_allowed"": false}",PASS,rule-001-01
pass_009,GH-002,"{""required_reviews"": 4, ""dismiss_stale_reviews"": true}",PASS,rule-002-02
pass_010,GH-001,"{""branch_protection_enabled"": true}",PASS,rule-001-01
...
fail_001,GH-001,"{""branch_protection_enabled"": false}",FAIL,rule-001-01
fail_002,GH-001,"{""branch_protection_enabled"": null}",FAIL,rule-001-01
fail_003,GH-002,"{""required_reviews"": 1}",FAIL,rule-002-01
fail_004,GH-002,"{""required_reviews"": 1, ""dismiss_stale_reviews"": false}",FAIL,rule-002-02
fail_005,GH-002,"{""required_reviews"": 2, ""dismiss_stale_reviews"": false}",FAIL,rule-002-02
fail_006,GH-003,"{""code_owner_review_required"": false}",FAIL,rule-003-01
fail_007,GH-001,"{""branch_protection_enabled"": false, ""force_push_allowed"": true}",FAIL,rule-001-01
fail_008,GH-002,"{""required_reviews"": 0}",FAIL,rule-002-01
fail_009,GH-003,"{""code_owner_review_required"": null}",FAIL,rule-003-01
fail_010,GH-001,"{""branch_protection_enabled"": false}",FAIL,rule-001-01
...
unknown_001,GH-001,"{""error"": ""403 Forbidden - Repository Access Denied""}",UNKNOWN,rule-001-01
unknown_002,GH-002,"{""error"": ""401 Unauthorized - Token Expired""}",UNKNOWN,rule-002-01
unknown_003,GH-003,"{""error"": ""404 Not Found - Repository Not Found""}",UNKNOWN,rule-003-01
unknown_004,GH-001,"{""error"": ""Timeout - GitHub API request exceeded 30s""}",UNKNOWN,rule-001-01
unknown_005,GH-002,"{""error"": ""GitHub rate limit exceeded""}",UNKNOWN,rule-002-02
unknown_006,GH-001,"{""error"": ""Invalid OAuth token""}",UNKNOWN,rule-001-01
unknown_007,GH-003,"{""error"": ""Branch does not exist""}",UNKNOWN,rule-003-01
unknown_008,GH-002,"{""error"": ""HTTP 500 - GitHub server error""}",UNKNOWN,rule-002-01
unknown_009,GH-001,"{""error"": ""Connection timeout""}",UNKNOWN,rule-001-01
unknown_010,GH-003,"{""error"": ""Permission denied""}",UNKNOWN,rule-003-01
...
# Total: 40 PASS + 40 FAIL + 20 UNKNOWN = 100 casos
```

---

## ANEXO 5: Carta Gantt Editable (Cronograma)

```
SECURECODE — Cronograma Crítico (85 días hábiles)

Inicio: 27-Ago-2026 | Fin: 09-Dic-2026

T1 | Formulación (10d)                    |========| [COMPLETADA]
T2 | Diseño Dominio (14d)                 |         |==============| [EN CURSO]
T3 | Spike GitHub (8d)                    |         |======| [COMPLETADA - 6d holgura]
T4 | Normalizador (12d)                   |                |============|
T5 | Conector GitHub (12d)                |                |============|
T6 | Motor Reglas (14d)                   |                         |==============|
T7 | Pruebas (10d)                        |                                    |==========|
T8 | Despliegue+Docs (8d)                 |                                              |========|
T9 | Buffer (5d)                          |                                                     |=====|

Hitos Institucionales:
  [09-Sep] ES1 Completado (15%)
  [28-Oct] ES2 Entrega (25%)
  [18-Nov] Presentación Impl (25%)
  [09-Dic] Defensa Final (35%)

Ruta Crítica: T1→T2→T4→T5→T6→T7→T8 (sin holgura)
Riesgo: Cualquier atraso en T2, T4, T5, T6 o T7 impacta fecha defensa
```

---

## ANEXO 6: Runbook de Recuperación ante Desastres (DRP)

### Escenario 1: Base de Datos PostgreSQL Caída

**Síntoma:** Conexión a PostgreSQL rechazada, error "connection refused"

**Paso a Paso:**

1. **Diagnóstico (< 1 min)**
   ```bash
   # Verificar Railway status
   railway logs -s postgres
   # Resultado: PostgreSQL pod crashed o out of memory
   ```

2. **Activación Backup (< 2 min)**
   ```bash
   # Railway managed DB automáticamente hace rollback a snapshot más reciente
   # Histórico de snapshots disponible 7 días
   railway db restore --backup-id <latest_backup_id>
   ```

3. **Validación (< 1 min)**
   ```bash
   # Reconectar y verificar integridad
   psql -c "SELECT COUNT(*) FROM evaluations"
   # Debe retornar número > 0
   ```

4. **Reinicio API (< 1 min)**
   ```bash
   # Railway auto-redeploy si DB se recupera
   # O manual:
   railway deploy
   ```

**RTO:** 5 minutos máximo  
**RPO:** 24 horas (backup diario 03:00 UTC)

---

### Escenario 2: Token GitHub Expirado

**Síntoma:** Ingesta diaria falla con 401 Unauthorized

**Paso a Paso:**

1. **Detectar (automático)**
   - CI/CD detecta fallo en tarea scheduler diaria
   - Alerta enviada a admin@securecode.local

2. **Rotación Token**
   ```bash
   # Generar nuevo token en GitHub:
   # Settings → Developer Settings → Personal Access Tokens → Generate new
   # Permisos: repo (read)
   
   # Actualizar en Railway Secrets:
   railway variables set GITHUB_API_TOKEN="ghp_new_token_here"
   ```

3. **Reintento Manual**
   ```bash
   # Triggear ingesta nuevamente:
   # (Endpoint interno)
   curl -X POST http://localhost:8000/internal/ingest-github \
     -H "Authorization: Bearer admin-token"
   ```

**RTO:** 10 minutos (rotación manual)  
**Preventivo:** Alarm 7 días antes de vencimiento

---

### Escenario 3: Corrupción de Datos Detectada (Hash Mismatch)

**Síntoma:** Evaluación retorna UNKNOWN pero evidencia_id no NULL. Hash no coincide.

**Paso a Paso:**

1. **Aislar Evidencia Corrupta**
   ```sql
   SELECT id, repository_id, hash_sha256, payload
   FROM evidences
   WHERE id = <corrupted_evidence_id>;
   
   -- Verificar si payload calculado != hash_sha256 almacenado
   ```

2. **Re-ingestión**
   ```bash
   # Forzar re-fetch desde GitHub
   curl -X POST http://localhost:8000/api/v1/repositories/<repo_id>/ingest \
     -H "Authorization: Bearer admin-token"
   ```

3. **Validar Recuperación**
   ```sql
   -- Nuevas evaluaciones deben tener hash correcto
   SELECT COUNT(*) FROM evaluations
   WHERE status != 'UNKNOWN' AND evidence_id = <new_evidence_id>;
   ```

**RTO:** 15 minutos  
**Causa Raíz:** Investigar logs para determinar si fue error cliente o servidor

---

## ANEXO 7: Matriz de Trazabilidad (Requisitos ↔ Pruebas)

```
REQ-001: Motor determinista
  └─ KPI-01: Reproducibilidad ≥99%
     └─ test_reproducibility (10 re-evaluaciones idénticas)
     └─ test_no_random_in_engine
     └─ test_no_datetime_in_engine

REQ-002: Ingesta GitHub API
  └─ test_github_client_get_branch_protection
  └─ test_github_normalizer_mapping
  └─ test_github_retry_on_429
  └─ test_github_timeout_handling

REQ-003: Evaluaciones inmutables
  └─ test_evaluations_insert_only (no UPDATE, no DELETE)
  └─ test_evaluation_hash_audit_trail
  └─ test_evaluation_integrity_constraints

REQ-004: Autenticación JWT
  └─ test_jwt_token_generation
  └─ test_jwt_token_validation
  └─ test_jwt_expiration
  └─ test_jwt_refresh_token

REQ-005: Ground Truth Validación
  └─ test_ground_truth_accuracy_gte_95
  └─ test_ground_truth_precision_gte_90
  └─ test_ground_truth_recall_gte_90
  └─ test_ground_truth_f1_score_gte_90

REQ-006: Latencia KPI-03
  └─ test_locust_p95_latency_lte_3s
  └─ test_locust_p99_latency_lte_8s
  └─ test_concurrency_100_concurrent_users

REQ-007: Disponibilidad 99.5%
  └─ test_healthcheck_responds_200
  └─ test_healthcheck_interval_60s
  └─ test_database_pool_size_10
  └─ test_restart_on_failure_policy

REQ-008: Seguridad TLS 1.3
  └─ test_https_endpoint_only
  └─ test_jwt_secrets_not_in_logs
  └─ test_password_hash_argon2
  └─ test_no_plaintext_credentials

REQ-009: Reportes Exportables
  └─ test_report_json_export
  └─ test_report_hmac_signature
  └─ test_report_pagination

REQ-010: Documentación OpenAPI
  └─ test_openapi_schema_valid
  └─ test_openapi_endpoints_documented
  └─ test_openapi_examples_working
```

---

## ANEXO 8: Especificación OpenAPI 3.0 (Resumida)

```yaml
openapi: 3.0.3
info:
  title: SECURECODE API
  version: 1.0.0
  description: Plataforma de evaluación automatizada de controles de ciberseguridad

servers:
  - url: https://api.securecode.local/api/v1
    description: Production

paths:
  /auth/login:
    post:
      summary: Autenticar usuario
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
      responses:
        '200':
          description: Autenticación exitosa
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  token_type:
                    type: string
                    example: bearer
                  expires_in:
                    type: integer
                    example: 86400

  /controls:
    get:
      summary: Listar controles
      parameters:
        - name: org_id
          in: query
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Lista de controles
    post:
      summary: Crear control
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ControlCreate'
      responses:
        '201':
          description: Control creado

  /evaluations:
    get:
      summary: Listar evaluaciones
      parameters:
        - name: control_id
          in: query
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Evaluaciones
    post:
      summary: Ejecutar evaluación
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                rule_id:
                  type: string
                  format: uuid
                repository_id:
                  type: string
                  format: uuid
      responses:
        '201':
          description: Evaluación creada

  /reports/compliance:
    get:
      summary: Generar reporte de cumplimiento
      parameters:
        - name: org_id
          in: query
          required: true
          schema:
            type: string
            format: uuid
        - name: export
          in: query
          schema:
            type: string
            enum: [json, pdf]
      responses:
        '200':
          description: Reporte

  /healthcheck:
    get:
      summary: Health check del servicio
      responses:
        '200':
          description: Servicio disponible
        '503':
          description: Servicio no disponible

components:
  schemas:
    ControlCreate:
      type: object
      required:
        - code
        - name
      properties:
        code:
          type: string
          maxLength: 50
        name:
          type: string
          maxLength: 255
        framework:
          type: string
          enum: [NIST-800-53, OWASP-ASVS, CUSTOM]

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
```

---

## ANEXO 9: Guía de Estilo y Convenciones de Código

### Convenciones Python (PEP 8)

```python
# Nombres
- snake_case para funciones y variables: def evaluate_rule()
- UPPER_CASE para constantes: MAX_RETRIES = 3
- PascalCase para clases: class RuleEvaluator

# Imports
from typing import Optional, List, Dict, Any
from app.domain.models import Rule, Evidence

# Docstrings (Google style)
def evaluate(rule: Rule, evidence: Optional[Evidence]) -> EvaluationStatus:
    """
    Evaluar regla contra evidencia.
    
    Args:
        rule: Regla con expresión declarativa
        evidence: Evidencia normalizada o None
    
    Returns:
        EvaluationStatus: PASS, FAIL, o UNKNOWN
    
    Raises:
        EvaluationError: Si la regla malformada
    """
    pass

# Type hints obligatorios
def calculate_hash(payload: Dict[str, Any]) -> str:
    ...

# Logging
logger.info("Evaluación completada", extra={"control_id": "...", "status": "PASS"})
```

### Conventional Commits

```
Formato:
<type>(<scope>): <subject>

<body>

<footer>

Ejemplos:
feat(engine): add AND operator support
  Allows combining multiple conditions in rules

feat(github): implement exponential backoff for rate limiting
  - Retry on 429 with Retry-After header
  - Max 3 retries with 1s, 2s, 4s delays

fix(auth): resolve JWT token expiration bug
  Token refresh endpoint was not updating TTL correctly

docs(api): add OpenAPI spec for /evaluations endpoints

test(ground-truth): add 20 UNKNOWN test cases

chore(deps): update sqlalchemy to 2.0.21
```

### Pull Request Checklist

- [ ] Tests pass locally (pytest)
- [ ] Code formatted (black)
- [ ] No linting errors (flake8)
- [ ] No secrets in code (bandit)
- [ ] Docstrings completos
- [ ] Type hints everywhere
- [ ] DB migrations versionadas (si aplica)
- [ ] CHANGELOG.md actualizado
- [ ] 2 approvals antes de merge

---

## ANEXO 10: Architecture Decision Records (ADRs)

### ADR-001: Usar Arquitectura Hexagonal

**Estado:** ACCEPTED  
**Fecha:** 2026-08-27

**Contexto:**
- SECURECODE necesita separar lógica de dominio de infraestructura
- Motor de reglas debe ser testeable independientemente de GitHub/PostgreSQL

**Decisión:**
Adoptar Arquitectura Hexagonal (Puertos y Adaptadores)

**Ventajas:**
- Core domain agnóstico de infraestructura
- Fácil testear motor sin mocks complejos
- Escalable a múltiples conectores futuros

**Consecuencias:**
- Más clases/interfaces (repositories, ports, adapters)
- Costo inicial de setup mayor

---

### ADR-002: Usar PostgreSQL + JSONB para Evidencia

**Estado:** ACCEPTED  
**Fecha:** 2026-08-27

**Contexto:**
- Evidencia es semi-estructurada (varía por fuente: GitHub, AWS, Azure)
- Necesario indexar y queryar campos específicos
- ACID guarantees crítico para evaluaciones

**Decisión:**
PostgreSQL 16 con tipo JSONB para payload, B-tree index en hash_sha256

**Ventajas:**
- ACID serializables
- JSONB indexable y queryable
- Backups native con pgBackrest
- Connection pooling nativo

**Consecuencias:**
- Dependencia de PostgreSQL (no soporta SQLite/MongoDB en MVP)
- Necesario Alembic para migraciones

---

### ADR-003: Motor Determinista sin State

**Estado:** ACCEPTED  
**Fecha:** 2026-08-28

**Contexto:**
- KPI-01 exige reproducibilidad 100%
- Necesario garantizar: misma entrada → siempre mismo resultado

**Decisión:**
Motor implementado como función pura:
- No usa random(), datetime.now()
- No depende de state externo
- No hace llamadas a APIs externas

**Ventajas:**
- Reproducibilidad garantizada (testeable)
- Parallelizable (sin race conditions)

**Consecuencias:**
- No puede cambiar lógica dinámicamente (se usa versioning de reglas)
- Cambios de regla requieren nueva versión explícita

---

### ADR-004: Ground Truth Dataset Validación Experimental

**Estado:** ACCEPTED  
**Fecha:** 2026-08-30

**Contexto:**
- Motor debe validarse contra casos conocidos
- Métrica: Accuracy ≥95%, Precision/Recall/F1 ≥0.90

**Decisión:**
Crear dataset de 100 casos controlados (40 PASS, 40 FAIL, 20 UNKNOWN)

**Ventajas:**
- Validación reproducible
- Matriz confusión auditable
- Detecta regresiones

**Consecuencias:**
- Require esfuerzo inicial en curation de casos
- Debe ser mantenido y versioned

---

**Fin de Anexos Completos**

