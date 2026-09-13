# SECURECODE — Especificación Técnica Completa para Desarrolladores

**Versión:** 2.0 (ES2 Corregido — 31 de agosto de 2026)  
**Proyecto:** Plataforma de Evaluación Automatizada de Cumplimiento de Controles de Ciberseguridad  
**Equipo:** Jonatthan Medalla (Motor + Dominio) | Jose Mora (Conector + Infraestructura)  
**Stack:** Python 3.12 | FastAPI 0.115.x | PostgreSQL 16 (Supabase) | Google Cloud Run

---

## 📋 TABLA DE CONTENIDOS

1. [Introducción y Visión](#introducción-y-visión)
2. [Estructura de Directorios y Bootstrapping](#estructura-de-directorios-y-bootstrapping)
3. [Modelo de Dominio (DDD)](#modelo-de-dominio-ddd)
4. [Esquema de Base de Datos (DDL PostgreSQL)](#esquema-de-base-de-datos-ddl-postgresql)
5. [Componentes y Puertos (Arquitectura Hexagonal)](#componentes-y-puertos-arquitectura-hexagonal)
6. [Especificación de APIs REST](#especificación-de-apis-rest)
7. [Conector GitHub: Ingesta y Normalización](#conector-github-ingesta-y-normalización)
8. [Motor de Reglas: Evaluación Determinista](#motor-de-reglas-evaluación-determinista)
9. [Autenticación y Seguridad](#autenticación-y-seguridad)
10. [Plan de Pruebas y Validación](#plan-de-pruebas-y-validación)
11. [CI/CD Pipeline (GitHub Actions)](#cicd-pipeline-github-actions)
12. [Despliegue en Supabase + Cloud Run](#despliegue-en-supabase--cloud-run)
13. [Monitoreo y Observabilidad](#monitoreo-y-observabilidad)
14. [Timeline de Desarrollo](#timeline-de-desarrollo)

---

## Introducción y Visión

### Problema Resuelto
**SECURECODE** automatiza la evaluación de controles de seguridad cuando la evidencia proviene de fuentes externas (GitHub, proveedores cloud, sistemas internos). Separa:
- **Control**: Qué requisito se verifica (ej: "Branch protection debe estar activo")
- **Regla**: Cómo se comprueba de forma declarativa (ej: `{required_reviews >= 2 AND dismiss_stale == true}`)
- **Evidencia**: Datos obtenidos de la fuente (ej: `{required_reviews: 2, dismiss_stale: true}` desde GitHub API)

### Estados del Motor
```
PASS     → La evidencia satisface la regla
FAIL     → La evidencia demuestra incumplimiento
UNKNOWN  → No hay datos suficientes (repo privado, token expirado, etc)
```

### MVP Alcance
**Incluido:**
- ✅ 1 conector GitHub API v3/v4 (solo lectura)
- ✅ Normalización canónica JSON + SHA-256
- ✅ Motor determinista (reproducibilidad 100%)
- ✅ Persistencia PostgreSQL 16 inmutable
- ✅ REST API + Usuario Admin único
- ✅ Reportes tabulares + export JSON

**Excluido (Roadmap Futuro):**
- ❌ Multi-tenancy
- ❌ RBAC granular
- ❌ Conectores AWS/Azure/GCP
- ❌ Remediación automática
- ❌ IA en núcleo de decisión

---

## Estructura de Directorios y Bootstrapping

### Árbol del Proyecto
```
securecode/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml           # Lint + Test + Build
│   │   └── deploy.yml       # Auto-deploy Cloud Run
│   └── CONTRIBUTING.md      # Convenciones Conventional Commits
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory + setup routes
│   ├── config.py            # Pydantic Settings (env vars)
│   │
│   ├── domain/              # Core Business Logic (DDD)
│   │   ├── __init__.py
│   │   ├── models.py        # Entities: Control, Rule, Evidence, Evaluation
│   │   ├── repositories/    # Repository interfaces (Ports)
│   │   │   ├── __init__.py
│   │   │   ├── control_repo.py
│   │   │   ├── rule_repo.py
│   │   │   ├── evidence_repo.py
│   │   │   └── evaluation_repo.py
│   │   ├── services/        # Business services (application layer)
│   │   │   ├── __init__.py
│   │   │   ├── control_service.py
│   │   │   ├── evaluation_service.py
│   │   │   └── report_service.py
│   │   └── engine/          # Motor de Reglas (Núcleo)
│   │       ├── __init__.py
│   │       ├── evaluator.py # Lógica PASS/FAIL/UNKNOWN
│   │       ├── types.py     # EvaluationStatus enum, Rule AST
│   │       └── exceptions.py
│   │
│   ├── adapters/            # Implementaciones concretas (Driven Adapters)
│   │   ├── __init__.py
│   │   ├── persistence/     # PostgreSQL ORM
│   │   │   ├── __init__.py
│   │   │   ├── database.py  # SQLAlchemy setup, connection pool
│   │   │   ├── models.py    # SQLAlchemy ORM models
│   │   │   └── repositories/ # Implementations
│   │   │       ├── __init__.py
│   │   │       ├── control_repo_pg.py
│   │   │       ├── rule_repo_pg.py
│   │   │       ├── evidence_repo_pg.py
│   │   │       └── evaluation_repo_pg.py
│   │   ├── github/          # GitHub API Adapter
│   │   │   ├── __init__.py
│   │   │   ├── client.py    # GitHub API HTTP client (asyncio)
│   │   │   ├── normalizer.py # Mapeo GitHub → esquema canónico
│   │   │   └── exceptions.py
│   │   └── auth/            # Autenticación
│   │       ├── __init__.py
│   │       └── jwt_handler.py
│   │
│   ├── api/                 # REST endpoints (Primary Adapters)
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py      # POST /auth/login, POST /auth/refresh
│   │   │   ├── controls.py  # CRUD /controls
│   │   │   ├── rules.py     # CRUD /rules
│   │   │   ├── evaluations.py # POST /evaluations, GET /evaluations
│   │   │   ├── repositories.py # GET /repositories (GitHub connect)
│   │   │   └── health.py    # GET /health, GET /healthcheck
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── logging.py   # Request/response logging + correlation ID
│   │
│   ├── scheduler/           # Scheduled jobs (Cron)
│   │   ├── __init__.py
│   │   ├── tasks.py         # @scheduled_task ingesta diaria
│   │   └── runner.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── hash.py          # SHA-256 hashing
│       ├── logger.py        # Structured logging (JSON)
│       └── exceptions.py    # Custom exceptions
│
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── unit/
│   │   ├── test_engine_evaluator.py
│   │   ├── test_normalizer.py
│   │   ├── test_auth.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_github_client.py
│   │   ├── test_persistence.py
│   │   └── ...
│   ├── e2e/
│   │   └── test_evaluation_flow.py
│   └── fixtures/
│       ├── ground_truth_dataset.csv  # 100 casos validación
│       └── mock_github_responses.json
│
├── db/
│   ├── alembic/             # Database migrations (Alembic)
│   │   ├── versions/
│   │   │   ├── 001_init_schema.py
│   │   │   └── ...
│   │   └── alembic.ini
│   └── ...
│
├── docs/
│   ├── API.md               # Especificación OpenAPI
│   ├── ARCHITECTURE.md      # Arquitectura detallada
│   ├── DDD_MODEL.md         # Domain-Driven Design
│   └── DEPLOYMENT.md        # Guía despliegue Supabase + Cloud Run
│
├── docker/
│   ├── Dockerfile           # Multistage: builder → runtime
│   ├── docker-compose.yml   # Local dev: FastAPI + PostgreSQL
│   └── .dockerignore
│
├── .env.example             # Variables entorno (NO commitear .env real)
├── .gitignore
├── pyproject.toml           # Configuración Python (proyecto moderno)
├── requirements.txt         # Dependencias pinned
├── requirements-dev.txt     # Dev: pytest, black, flake8, etc
├── pytest.ini               # Configuración pytest
├── .flake8                  # Linting rules
├── .pre-commit-config.yaml  # Git hooks
│
├── README.md                # Readme general proyecto
└── CONTRIBUTING.md          # Guía para contribuidores

```

### Quickstart: Configuración Local

#### Prerequisites
```bash
# Sistema operativo: Ubuntu 22.04+ / macOS 12+ / Windows WSL2
# Python 3.12
# PostgreSQL 16
# Docker + Docker Compose (opcional, para dev local)

python --version  # 3.12.0 mínimo
pip install uv   # Manejador de paquetes rápido (opcional)
```

#### Setup Dev Environment
```bash
# 1. Clonar repo
git clone https://github.com/securecode/securecode.git
cd securecode

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Copiar .env.example → .env y ajustar
cp .env.example .env
# Editar: DATABASE_URL, GITHUB_OAUTH_TOKEN, etc

# 5. Inicializar base de datos
alembic upgrade head

# 6. Ejecutar app local
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. Tests
pytest tests/ -v --cov=app --cov-report=html

# 8. Linting
black app tests
flake8 app tests
```

### Configuración (.env)
```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/securecode_dev
DATABASE_POOL_SIZE=10
DATABASE_ECHO=false  # true en dev para ver SQL

# GitHub
GITHUB_API_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_API_VERSION=2022-11-28

# Autenticación
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-xxxxxxxxxxxxxxxxx
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24h
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Aplicación
APP_ENV=development  # development | staging | production
APP_DEBUG=true
LOG_LEVEL=DEBUG

# Admin usuario (seedear en DB)
ADMIN_EMAIL=admin@securecode.local
ADMIN_PASSWORD_HASH=...  # Pre-hashed con Argon2
```

---

## Modelo de Dominio (DDD)

### Entidades Principales

#### 1. **Control** (Entity)
Requisito de seguridad a verificar. Inmutable salvo version.

```python
# app/domain/models.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class Framework(Enum):
    """Marcos normativos"""
    NIST_800_53 = "NIST-800-53"
    OWASP_ASVS = "OWASP-ASVS"
    CUSTOM = "CUSTOM"

@dataclass(frozen=True)
class Control:
    """Entidad: Control de Seguridad"""
    id: UUID
    org_id: UUID
    code: str  # ej: "GH-001"
    name: str  # ej: "Branch Protection Requerido"
    description: str
    framework: Optional[Framework] = None
    severity: str  # "CRITICAL" | "HIGH" | "MEDIUM"
    created_at: datetime = None
    updated_at: datetime = None
    
    @staticmethod
    def create(org_id: UUID, code: str, name: str, description: str, 
               framework: Optional[Framework] = None, severity: str = "MEDIUM") -> "Control":
        """Factory method con validación"""
        if not code or len(code) > 50:
            raise ValueError(f"Control code invalid: {code}")
        if not name or len(name) > 255:
            raise ValueError(f"Control name invalid: {name}")
        return Control(
            id=UUID(version=4),
            org_id=org_id,
            code=code,
            name=name,
            description=description,
            framework=framework,
            severity=severity,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
```

#### 2. **Rule** (Entity + Value Object)
Expresión declarativa que define cómo se comprueba un control.

```python
from enum import Enum
from typing import Dict, Any, Union
import json

class RuleOperator(Enum):
    """Operadores soportados"""
    EQ = "=="       # Igualdad
    NEQ = "!="      # Desigualdad
    GT = ">"        # Mayor que
    GTE = ">="      # Mayor o igual
    LT = "<"        # Menor que
    LTE = "<="      # Menor o igual
    AND = "AND"     # AND lógico
    OR = "OR"       # OR lógico
    IN = "in"       # Pertenencia en lista

@dataclass(frozen=True)
class RuleExpression:
    """Value Object: Expresión de regla declarativa"""
    operator: RuleOperator
    left: Union[str, "RuleExpression"]  # Campo o sub-expresión
    right: Union[Any, "RuleExpression"]  # Valor o sub-expresión
    
    def to_json(self) -> Dict[str, Any]:
        """Serializar a JSON para almacenar en JSONB"""
        return {
            "operator": self.operator.value,
            "left": self.left if isinstance(self.left, str) else self.left.to_json(),
            "right": self.right if not isinstance(self.right, RuleExpression) else self.right.to_json(),
        }
    
    @staticmethod
    def from_json(data: Dict[str, Any]) -> "RuleExpression":
        """Deserializar desde JSON"""
        # Implementación recursiva
        pass

@dataclass(frozen=True)
class Rule:
    """Entidad: Regla de Evaluación"""
    id: UUID
    control_id: UUID
    expression: RuleExpression  # Estructura anidable
    version: int = 1
    is_active: bool = True
    created_at: datetime = None
    
    @staticmethod
    def create(control_id: UUID, expression_json: Dict[str, Any]) -> "Rule":
        """Factory con validación"""
        expr = RuleExpression.from_json(expression_json)
        return Rule(
            id=UUID(version=4),
            control_id=control_id,
            expression=expr,
            version=1,
            is_active=True,
            created_at=datetime.utcnow(),
        )
```

#### 3. **Evidence** (Entity)
Datos normalizados obtenidos de la fuente externa.

```python
from typing import Dict

@dataclass(frozen=True)
class Evidence:
    """Entidad: Evidencia Normalizada"""
    id: UUID
    repository_id: UUID
    payload: Dict[str, Any]  # JSON normalizado
    hash_sha256: str  # CHAR(64)
    source: str  # "github" | "aws" | "azure" | ...
    created_at: datetime
    
    @staticmethod
    def create(repo_id: UUID, payload: Dict[str, Any], source: str = "github") -> "Evidence":
        """Factory con cálculo de hash"""
        # Normalizar: sort_keys, separators compactos
        json_canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        hash_sha256 = sha256(json_canonical.encode()).hexdigest()
        
        return Evidence(
            id=UUID(version=4),
            repository_id=repo_id,
            payload=payload,
            hash_sha256=hash_sha256,
            source=source,
            created_at=datetime.utcnow(),
        )
```

#### 4. **Evaluation** (Entity + Result)
Resultado de evaluar una regla contra evidencia.

```python
from enum import Enum

class EvaluationStatus(Enum):
    """Estados posibles de evaluación"""
    PASS = "PASS"        # Cumple
    FAIL = "FAIL"        # Incumple
    UNKNOWN = "UNKNOWN"  # Evidencia insuficiente

@dataclass(frozen=True)
class Evaluation:
    """Entidad: Resultado de Evaluación"""
    id: UUID
    rule_id: UUID
    evidence_id: Optional[UUID]  # NULL si UNKNOWN
    status: EvaluationStatus
    evaluated_at: datetime
    evidence_hash_at_time: str  # Auditoría histórica
    
    @staticmethod
    def create(rule_id: UUID, evidence_id: Optional[UUID], 
               status: EvaluationStatus, hash_at_time: str) -> "Evaluation":
        return Evaluation(
            id=UUID(version=4),
            rule_id=rule_id,
            evidence_id=evidence_id,
            status=status,
            evaluated_at=datetime.utcnow(),
            evidence_hash_at_time=hash_at_time,
        )
```

### Repository Interfaces (Puertos - DDD)

```python
# app/domain/repositories/evaluation_repo.py

from abc import ABC, abstractmethod
from typing import List, Optional

class EvaluationRepository(ABC):
    """Puerto: Interfaz de persistencia para Evaluations"""
    
    @abstractmethod
    async def save(self, evaluation: Evaluation) -> Evaluation:
        """Persistir evaluación inmutable"""
        pass
    
    @abstractmethod
    async def find_by_id(self, evaluation_id: UUID) -> Optional[Evaluation]:
        pass
    
    @abstractmethod
    async def find_by_rule(self, rule_id: UUID, limit: int = 100) -> List[Evaluation]:
        """Evaluaciones de una regla (histórico)"""
        pass
    
    @abstractmethod
    async def find_by_control(self, control_id: UUID, org_id: UUID) -> List[Evaluation]:
        """Evaluaciones de un control (para reportes)"""
        pass
```

---

## Esquema de Base de Datos (DDL PostgreSQL)

### SQL DDL Completo

```sql
-- db/alembic/versions/001_init_schema.py (en formato Alembic)
-- O como SQL puro:

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabla: Organizations (Multi-tenancy ready)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- Argon2
    role VARCHAR(20) NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'analyst', 'viewer')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- Tabla: Controls
CREATE TABLE controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    framework VARCHAR(100),  -- "NIST-800-53", "OWASP-ASVS", etc
    severity VARCHAR(20) CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, code)
);
CREATE INDEX idx_controls_org_id ON controls(org_id);

-- Tabla: Rules
CREATE TABLE rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    expression JSONB NOT NULL,  -- Expresión declarativa
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rules_control_id ON rules(control_id);
CREATE INDEX idx_rules_is_active ON rules(is_active);

-- Tabla: Repositories (fuentes a evaluar)
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,  -- "example-repo"
    owner VARCHAR(255) NOT NULL,  -- "github-org"
    url VARCHAR(255) NOT NULL UNIQUE,  -- "https://github.com/github-org/example-repo"
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, owner, name)
);
CREATE INDEX idx_repositories_org_id ON repositories(org_id);

-- Tabla: Evidences (Normalizada + Hash)
CREATE TABLE evidences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,  -- Datos normalizados
    hash_sha256 CHAR(64) NOT NULL,  -- SHA-256 fingerprint
    source VARCHAR(40) NOT NULL DEFAULT 'github',  -- Tipo de fuente
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_evidences_repository_id ON evidences(repository_id);
CREATE INDEX idx_evidences_hash_sha256 ON evidences(hash_sha256);
CREATE INDEX idx_evidences_created_at ON evidences(created_at);

-- Tabla: Evaluations (Resultados Inmutables)
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    evidence_id UUID REFERENCES evidences(id) ON DELETE SET NULL,  -- NULL si UNKNOWN
    status VARCHAR(20) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'UNKNOWN')),
    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evidence_hash_at_time CHAR(64) NOT NULL,  -- Auditoría: qué hash se usó
    
    CONSTRAINT evaluation_status_consistency CHECK (
        (status = 'UNKNOWN' AND evidence_id IS NULL) OR
        (status IN ('PASS', 'FAIL') AND evidence_id IS NOT NULL)
    )
);
CREATE INDEX idx_evaluations_rule_id ON evaluations(rule_id);
CREATE INDEX idx_evaluations_evidence_id ON evaluations(evidence_id);
CREATE INDEX idx_evaluations_status ON evaluations(status);
CREATE INDEX idx_evaluations_evaluated_at ON evaluations(evaluated_at);

-- Tabla: Audit Logs (Trazabilidad de Acciones)
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,  -- "LOGIN", "DOWNLOAD_REPORT", "CREATE_CONTROL", etc
    details JSONB,  -- Contexto adicional
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### Alembic Migration (Python)

```python
# db/alembic/versions/001_init_schema.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import uuid4

def upgrade() -> None:
    """Crear schema inicial"""
    # Extensiones
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Organizations
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # ... resto de tablas (similar patrón)

def downgrade() -> None:
    """Revertir schema"""
    op.drop_table('audit_logs')
    op.drop_table('evaluations')
    op.drop_table('evidences')
    op.drop_table('repositories')
    op.drop_table('rules')
    op.drop_table('controls')
    op.drop_table('users')
    op.drop_table('organizations')
```

---

## Componentes y Puertos (Arquitectura Hexagonal)

### Core Domain: Motor de Reglas

```python
# app/domain/engine/evaluator.py

from typing import Dict, Any, Optional
from app.domain.models import Rule, Evidence, EvaluationStatus, RuleExpression, RuleOperator
from app.domain.engine.types import EvaluationError

class RuleEvaluator:
    """
    Motor de reglas determinista.
    
    Propiedades:
    - Reproducibilidad: eval(rule, evidencia) siempre produce mismo resultado
    - Sin efectos laterales: No depende de time(), random(), estado externo
    - Función pura: Same input → Same output
    """
    
    def evaluate(self, rule: Rule, evidence: Optional[Evidence]) -> EvaluationStatus:
        """
        Evaluar una regla contra evidencia.
        
        Args:
            rule: Regla con expresión declarativa
            evidence: Evidencia normalizada o None (para UNKNOWN)
        
        Returns:
            EvaluationStatus: PASS, FAIL, o UNKNOWN
        
        Raises:
            EvaluationError: Si la regla está malformada
        """
        # Paso 1: Si no hay evidencia, resultado es UNKNOWN
        if evidence is None:
            return EvaluationStatus.UNKNOWN
        
        try:
            # Paso 2: Evaluar expresión contra payload de evidencia
            result = self._eval_expression(rule.expression, evidence.payload)
            
            # Paso 3: Mapear resultado booleano a PASS/FAIL
            return EvaluationStatus.PASS if result else EvaluationStatus.FAIL
        
        except KeyError:
            # Campo requerido no presente en evidencia → UNKNOWN
            return EvaluationStatus.UNKNOWN
        except Exception as e:
            raise EvaluationError(f"Rule evaluation failed: {e}")
    
    def _eval_expression(self, expr: RuleExpression, evidence: Dict[str, Any]) -> bool:
        """Evaluar expresión recursiva contra evidencia"""
        
        if expr.operator == RuleOperator.EQ:
            left_val = self._get_value(expr.left, evidence)
            right_val = expr.right
            return left_val == right_val
        
        elif expr.operator == RuleOperator.NEQ:
            left_val = self._get_value(expr.left, evidence)
            return left_val != expr.right
        
        elif expr.operator == RuleOperator.GT:
            left_val = self._get_value(expr.left, evidence)
            return left_val > expr.right
        
        elif expr.operator == RuleOperator.GTE:
            left_val = self._get_value(expr.left, evidence)
            return left_val >= expr.right
        
        elif expr.operator == RuleOperator.LT:
            left_val = self._get_value(expr.left, evidence)
            return left_val < expr.right
        
        elif expr.operator == RuleOperator.LTE:
            left_val = self._get_value(expr.left, evidence)
            return left_val <= expr.right
        
        elif expr.operator == RuleOperator.AND:
            left_result = self._eval_expression(expr.left, evidence)
            right_result = self._eval_expression(expr.right, evidence)
            return left_result and right_result
        
        elif expr.operator == RuleOperator.OR:
            left_result = self._eval_expression(expr.left, evidence)
            right_result = self._eval_expression(expr.right, evidence)
            return left_result or right_result
        
        elif expr.operator == RuleOperator.IN:
            left_val = self._get_value(expr.left, evidence)
            return left_val in expr.right
        
        else:
            raise EvaluationError(f"Unknown operator: {expr.operator}")
    
    def _get_value(self, left: Any, evidence: Dict[str, Any]) -> Any:
        """Extraer valor de evidencia si es clave, o retornar valor literal"""
        if isinstance(left, str):
            # Es clave en evidencia (dot notation: "branch_protection.enabled")
            return self._get_nested(evidence, left)
        else:
            # Es sub-expresión
            return self._eval_expression(left, evidence)
    
    def _get_nested(self, obj: Dict[str, Any], path: str) -> Any:
        """Acceso nested: 'branch_protection.enabled' → obj['branch_protection']['enabled']"""
        keys = path.split('.')
        for key in keys:
            obj = obj[key]  # Raises KeyError si falta
        return obj
```

### Conector GitHub: Normalización

```python
# app/adapters/github/normalizer.py

import json
from hashlib import sha256
from typing import Dict, Any
from app.domain.models import Evidence

class GitHubNormalizer:
    """
    Mapeo desde respuesta GitHub API → Esquema Canónico JSON.
    
    Ejemplo:
        GitHub Response: {
            "protected": true,
            "required_pull_request_reviews": {
                "required_approving_review_count": 2,
                "dismiss_stale_reviews": true,
                "require_code_owner_reviews": true,
            },
            ...
        }
        
        Canonical: {
            "branch_protection_enabled": true,
            "required_reviews": 2,
            "dismiss_stale_reviews": true,
            "code_owner_review_required": true,
        }
    """
    
    # Mapping GitHub → Canonical
    MAPPINGS = {
        "protected": "branch_protection_enabled",
        "required_pull_request_reviews.required_approving_review_count": "required_reviews",
        "required_pull_request_reviews.dismiss_stale_reviews": "dismiss_stale_reviews",
        "required_pull_request_reviews.require_code_owner_reviews": "code_owner_review_required",
        # ... más mappings
    }
    
    def normalize(self, github_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizar respuesta GitHub a esquema canónico.
        
        Args:
            github_payload: Respuesta bruta de GitHub API
        
        Returns:
            Dict canónico normalizado
        """
        canonical = {}
        
        for github_path, canonical_key in self.MAPPINGS.items():
            value = self._get_nested(github_payload, github_path)
            if value is not None:
                canonical[canonical_key] = value
        
        return canonical
    
    def _get_nested(self, obj: Dict[str, Any], path: str) -> Any:
        """Acceso anidado con default None"""
        keys = path.split('.')
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj
    
    @staticmethod
    def calculate_hash(canonical: Dict[str, Any]) -> str:
        """
        Calcular SHA-256 de evidencia canónica.
        
        Garantías:
        - Reproducible: mismos datos → siempre mismo hash
        - Independente orden: sort_keys=True
        """
        json_str = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        return sha256(json_str.encode()).hexdigest()
```

---

## Especificación de APIs REST

### Autenticación

#### POST /auth/login
```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@securecode.local",
  "password": "admin-password-123"
}

# Response 200
{
  "access_token": "eyJhbGc...",  # JWT HS256, TTL 24h
  "refresh_token": "eyJhbGc...", # JWT HS256, TTL 7d
  "token_type": "bearer",
  "expires_in": 86400
}

# Response 401
{
  "detail": "Invalid credentials"
}
```

### Controles

#### POST /api/v1/controls
```http
POST /api/v1/controls HTTP/1.1
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "code": "GH-001",
  "name": "Branch Protection Required",
  "description": "El repositorio debe tener branch protection habilitado",
  "framework": "NIST-800-53",
  "severity": "HIGH"
}

# Response 201
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "GH-001",
  "name": "Branch Protection Required",
  "created_at": "2026-09-01T10:30:00Z"
}
```

#### GET /api/v1/controls?org_id=...
```http
GET /api/v1/controls?org_id=550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer eyJhbGc...

# Response 200
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "code": "GH-001",
      "name": "Branch Protection Required",
      "severity": "HIGH",
      "created_at": "2026-09-01T10:30:00Z"
    },
    ...
  ],
  "total": 5,
  "page": 1,
  "page_size": 10
}
```

### Evaluaciones

#### POST /api/v1/evaluations
```http
POST /api/v1/evaluations HTTP/1.1
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "rule_id": "550e8400-e29b-41d4-a716-446655440010",
  "repository_id": "550e8400-e29b-41d4-a716-446655440020"
}

# Response 202 Accepted (evaluación asincrónica)
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440030",
  "status": "processing"
}

# O Response 200 (si sincrónica)
{
  "id": "550e8400-e29b-41d4-a716-446655440030",
  "rule_id": "550e8400-e29b-41d4-a716-446655440010",
  "evidence_id": "550e8400-e29b-41d4-a716-446655440040",
  "status": "PASS",
  "evaluated_at": "2026-09-01T10:35:00Z",
  "evidence_hash_at_time": "abc123def456..."
}
```

#### GET /api/v1/evaluations?control_id=...
```http
GET /api/v1/evaluations?control_id=550e8400-e29b-41d4-a716-446655440001 HTTP/1.1
Authorization: Bearer eyJhbGc...

# Response 200
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "control_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "PASS",
      "evaluated_at": "2026-09-01T10:35:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440031",
      "control_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "FAIL",
      "evaluated_at": "2026-09-01T11:00:00Z"
    },
    ...
  ],
  "total": 12,
  "statistics": {
    "pass_count": 8,
    "fail_count": 3,
    "unknown_count": 1,
    "pass_percentage": 66.67
  }
}
```

### Reportes

#### GET /api/v1/reports/compliance
```http
GET /api/v1/reports/compliance?org_id=...&export=json HTTP/1.1
Authorization: Bearer eyJhbGc...

# Response 200
{
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_at": "2026-09-01T11:30:00Z",
  "signature": "HMAC-SHA256=abc123def456...",  # Para integridad
  "controls": [
    {
      "code": "GH-001",
      "name": "Branch Protection Required",
      "severity": "HIGH",
      "latest_evaluation": {
        "status": "PASS",
        "evaluated_at": "2026-09-01T10:35:00Z"
      },
      "repositories": [
        {
          "name": "example-repo",
          "status": "PASS",
          "evidence_hash": "abc123def456..."
        },
        ...
      ]
    },
    ...
  ],
  "summary": {
    "total_controls": 5,
    "passing": 4,
    "failing": 1,
    "unknown": 0,
    "compliance_percentage": 80.0
  }
}

# Si export=pdf, retorna PDF binario
```

### Health Check

#### GET /healthcheck
```http
GET /healthcheck HTTP/1.1

# Response 200
{
  "status": "healthy",
  "timestamp": "2026-09-01T11:35:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "up",
    "github_api": "up"  # Ping a GitHub cada cierto tiempo
  }
}

# Response 503 (si hay problemas)
{
  "status": "unhealthy",
  "timestamp": "2026-09-01T11:36:00Z",
  "checks": {
    "database": "down",
    "github_api": "up"
  }
}
```

---

## Conector GitHub: Ingesta y Normalización

### Client GitHub (Async)

```python
# app/adapters/github/client.py

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from app.config import settings
from app.adapters.github.exceptions import GitHubError

class GitHubClient:
    """
    Cliente asincrónico para GitHub API v3/v4.
    
    Características:
    - Manejo automático de rate limiting (429)
    - Reintentos con backoff exponencial
    - Timeout configurado
    - Logging de requests
    """
    
    API_BASE = "https://api.github.com"
    MAX_RETRIES = 3
    BACKOFF_SECONDS = [1, 2, 4]  # Exponential backoff
    TIMEOUT_SECONDS = 30
    
    def __init__(self, token: str):
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": settings.GITHUB_API_VERSION,
            "User-Agent": "SECURECODE/1.0",
        }
    
    async def get_branch_protection(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """
        GET /repos/{owner}/{repo}/branches/{branch}/protection
        
        Raises:
            GitHubError: Si la rama no existe o permisos insuficientes
        """
        endpoint = f"/repos/{owner}/{repo}/branches/{branch}/protection"
        return await self._request("GET", endpoint)
    
    async def get_required_reviews(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """
        GET /repos/{owner}/{repo}/branches/{branch}/required_status_checks
        """
        endpoint = f"/repos/{owner}/{repo}/branches/{branch}/required_status_checks"
        return await self._request("GET", endpoint)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Hacer request a GitHub con reintentos y manejo de rate limiting.
        
        Manejo de errores:
        - 403: GitHub rate limit exceeded → esperar Retry-After header
        - 401: Token inválido o expirado → raise GitHubError
        - 404: Recurso no encontrado → raise GitHubError
        - 5xx: Error servidor → reintento
        """
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = self.API_BASE + endpoint
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS),
                    **kwargs
                ) as resp:
                    
                    if resp.status == 200:
                        return await resp.json()
                    
                    elif resp.status == 429:
                        # Rate limit exceeded
                        retry_after = int(resp.headers.get('Retry-After', 60))
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise GitHubError(f"Rate limit exceeded after {self.MAX_RETRIES} retries")
                    
                    elif resp.status == 401:
                        raise GitHubError("Unauthorized: Invalid or expired token")
                    
                    elif resp.status == 404:
                        raise GitHubError(f"Not found: {endpoint}")
                    
                    elif resp.status >= 500:
                        # Server error - reintento
                        if attempt < self.MAX_RETRIES - 1:
                            backoff = self.BACKOFF_SECONDS[attempt]
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            raise GitHubError(f"GitHub server error {resp.status}")
                    
                    else:
                        raise GitHubError(f"Unexpected status {resp.status}: {await resp.text()}")
            
            except asyncio.TimeoutError:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.BACKOFF_SECONDS[attempt])
                    continue
                else:
                    raise GitHubError(f"Timeout after {self.MAX_RETRIES} retries")
    
    async def close(self):
        """Cerrar sesión aiohttp"""
        if self.session:
            await self.session.close()
    
    def __del__(self):
        """Cleanup en destructor"""
        if self.session and not self.session.closed:
            asyncio.run_coroutine_threadsafe(self.session.close(), asyncio.get_event_loop())
```

### Ingesta Programada

```python
# app/scheduler/tasks.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.adapters.github.client import GitHubClient
from app.adapters.github.normalizer import GitHubNormalizer
from app.domain.repositories import RepositoryRepository, EvidenceRepository

class IngestionScheduler:
    """
    Tarea programada: Ingestar evidencia de GitHub diariamente a las 02:00 UTC.
    
    Flujo:
    1. Conectar a GitHub API (con token)
    2. Por cada repositorio autorizado: obtener branch protection
    3. Normalizar respuesta
    4. Calcular SHA-256
    5. Persistir en BD
    6. Registrar en audit_logs
    """
    
    def __init__(self, scheduler: AsyncIOScheduler, 
                 repo_repo: RepositoryRepository,
                 evidence_repo: EvidenceRepository):
        self.scheduler = scheduler
        self.repo_repo = repo_repo
        self.evidence_repo = evidence_repo
        self.normalizer = GitHubNormalizer()
    
    async def ingest_daily(self):
        """Tarea diaria de ingesta"""
        try:
            client = GitHubClient(settings.GITHUB_API_TOKEN)
            
            # Obtener todos los repositorios autorizados
            repos = await self.repo_repo.find_all_active()
            
            for repo in repos:
                try:
                    # Obtener branch protection de GitHub
                    github_payload = await client.get_branch_protection(
                        owner=repo.owner,
                        repo=repo.name,
                        branch="main"
                    )
                    
                    # Normalizar
                    canonical = self.normalizer.normalize(github_payload)
                    hash_val = GitHubNormalizer.calculate_hash(canonical)
                    
                    # Persistir
                    evidence = Evidence.create(
                        repo_id=repo.id,
                        payload=canonical,
                        source="github"
                    )
                    await self.evidence_repo.save(evidence)
                    
                    # Auditoría
                    await audit_log(repo.org_id, None, "GITHUB_INGEST_SUCCESS", {
                        "repo_id": str(repo.id),
                        "hash": hash_val
                    })
                
                except GitHubError as e:
                    # Registrar evidencia UNKNOWN
                    evidence = Evidence.create(
                        repo_id=repo.id,
                        payload={"error": str(e)},
                        source="github"
                    )
                    await self.evidence_repo.save(evidence)
                    
                    await audit_log(repo.org_id, None, "GITHUB_INGEST_FAILED", {
                        "repo_id": str(repo.id),
                        "error": str(e)
                    })
            
            await client.close()
        
        except Exception as e:
            logger.error(f"Daily ingestion failed: {e}", exc_info=True)
    
    def start(self):
        """Programar tarea"""
        self.scheduler.add_job(
            self.ingest_daily,
            "cron",
            hour=2,  # 02:00 UTC
            minute=0,
            id="daily_github_ingest"
        )
        self.scheduler.start()
```

---

## Motor de Reglas: Evaluación Determinista

### Servicio de Evaluación

```python
# app/domain/services/evaluation_service.py

from typing import Optional
from app.domain.models import Rule, Evidence, Evaluation, EvaluationStatus
from app.domain.engine.evaluator import RuleEvaluator
from app.domain.repositories import (
    EvaluationRepository, EvidenceRepository, RuleRepository
)

class EvaluationService:
    """
    Servicio de aplicación: Orquesta evaluación de reglas.
    
    Responsabilidades:
    1. Obtener regla y evidencia
    2. Evaluar determinísticamente
    3. Persistir resultado
    4. Retornar resultado
    """
    
    def __init__(self, 
                 evaluator: RuleEvaluator,
                 rule_repo: RuleRepository,
                 evidence_repo: EvidenceRepository,
                 eval_repo: EvaluationRepository):
        self.evaluator = evaluator
        self.rule_repo = rule_repo
        self.evidence_repo = evidence_repo
        self.eval_repo = eval_repo
    
    async def evaluate_rule_against_evidence(
        self,
        rule_id: str,
        evidence_id: Optional[str]
    ) -> Evaluation:
        """
        Punto de entrada: Evaluar regla contra evidencia específica.
        
        Garantías:
        - Determinismo: mismos inputs → mismo output
        - Reproducibilidad: resultado auditado con hash de evidencia
        """
        
        # Paso 1: Obtener regla y evidencia
        rule = await self.rule_repo.find_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")
        
        evidence: Optional[Evidence] = None
        if evidence_id:
            evidence = await self.evidence_repo.find_by_id(evidence_id)
        
        # Paso 2: Evaluar determinísticamente
        status = self.evaluator.evaluate(rule, evidence)
        
        # Paso 3: Persistir resultado (inmutable)
        evidence_hash = evidence.hash_sha256 if evidence else "none"
        evaluation = Evaluation.create(
            rule_id=rule.id,
            evidence_id=evidence.id if evidence else None,
            status=status,
            hash_at_time=evidence_hash
        )
        
        await self.eval_repo.save(evaluation)
        
        # Paso 4: Retornar
        return evaluation
    
    async def get_control_compliance_summary(
        self,
        control_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """
        Resumen de cumplimiento de un control.
        
        Retorna:
        {
            "control_id": "...",
            "pass_count": 8,
            "fail_count": 2,
            "unknown_count": 1,
            "compliance_percentage": 80.0,
            "latest_evaluations": [...]
        }
        """
        evals = await self.eval_repo.find_by_control(control_id, org_id)
        
        pass_count = len([e for e in evals if e.status == EvaluationStatus.PASS])
        fail_count = len([e for e in evals if e.status == EvaluationStatus.FAIL])
        unknown_count = len([e for e in evals if e.status == EvaluationStatus.UNKNOWN])
        
        total_decidable = pass_count + fail_count
        compliance_pct = (pass_count / total_decidable * 100) if total_decidable > 0 else 0
        
        return {
            "control_id": control_id,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "unknown_count": unknown_count,
            "compliance_percentage": compliance_pct,
            "total_evaluations": len(evals),
            "latest_evaluations": sorted(evals, key=lambda e: e.evaluated_at, reverse=True)[:10]
        }
```

---

## Autenticación y Seguridad

### JWT Handler

```python
# app/adapters/auth/jwt_handler.py

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings

class TokenPayload(BaseModel):
    """Payload del JWT"""
    sub: str  # email del usuario
    exp: int  # expiration timestamp
    iat: int  # issued at
    token_type: str  # "access" | "refresh"

class JWTHandler:
    """Generación y validación de JWT HS256"""
    
    ALGORITHM = "HS256"
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    @classmethod
    def create_access_token(cls, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Crear JWT access token (TTL 24h por defecto)
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "sub": email,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "token_type": "access",
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=cls.ALGORITHM
        )
        return encoded_jwt
    
    @classmethod
    def create_refresh_token(cls, email: str) -> str:
        """
        Crear JWT refresh token (TTL 7d)
        """
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        to_encode = {
            "sub": email,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "token_type": "refresh",
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=cls.ALGORITHM
        )
        return encoded_jwt
    
    @classmethod
    def verify_token(cls, token: str, token_type: str = "access") -> TokenPayload:
        """
        Verificar y decodificar JWT.
        
        Raises:
            jwt.ExpiredSignatureError: Token expirado
            jwt.InvalidTokenError: Token inválido
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            
            token_type_from_payload = payload.get("token_type")
            if token_type_from_payload != token_type:
                raise jwt.InvalidTokenError(f"Token type mismatch: expected {token_type}")
            
            return TokenPayload(**payload)
        
        except jwt.ExpiredSignatureError:
            raise  # Re-raise
        except jwt.InvalidTokenError:
            raise
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash de contraseña con Argon2"""
        return cls.pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain: str, hashed: str) -> bool:
        """Verificar contraseña contra hash"""
        return cls.pwd_context.verify(plain, hashed)
```

### Dependency Injection & FastAPI

```python
# app/api/deps.py

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.adapters.auth.jwt_handler import JWTHandler
from app.domain.repositories import UserRepository

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    user_repo: UserRepository = Depends(lambda: UserRepository())
):
    """
    Dependency: Obtener usuario actual autenticado desde JWT.
    
    Raises:
        HTTPException 401: Token inválido o expirado
    """
    try:
        token_payload = JWTHandler.verify_token(credentials.credentials, token_type="access")
        user = await user_repo.find_by_email(token_payload.sub)
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return user
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
```

---

## Plan de Pruebas y Validación

### Unit Tests: Motor de Reglas

```python
# tests/unit/test_engine_evaluator.py

import pytest
from app.domain.engine.evaluator import RuleEvaluator
from app.domain.models import (
    Rule, Evidence, EvaluationStatus, RuleExpression, RuleOperator
)

class TestRuleEvaluator:
    """Unit tests: Motor determinista"""
    
    @pytest.fixture
    def evaluator(self):
        return RuleEvaluator()
    
    def test_evaluate_eq_true(self, evaluator):
        """Test: Igualdad verdadera"""
        expr = RuleExpression(RuleOperator.EQ, "branch_protection_enabled", True)
        rule = Rule(id=..., control_id=..., expression=expr)
        evidence = Evidence.create(
            repo_id=...,
            payload={"branch_protection_enabled": True}
        )
        
        result = evaluator.evaluate(rule, evidence)
        assert result == EvaluationStatus.PASS
    
    def test_evaluate_eq_false(self, evaluator):
        """Test: Igualdad falsa"""
        expr = RuleExpression(RuleOperator.EQ, "branch_protection_enabled", True)
        rule = Rule(id=..., control_id=..., expression=expr)
        evidence = Evidence.create(
            repo_id=...,
            payload={"branch_protection_enabled": False}
        )
        
        result = evaluator.evaluate(rule, evidence)
        assert result == EvaluationStatus.FAIL
    
    def test_evaluate_missing_field(self, evaluator):
        """Test: Campo faltante → UNKNOWN"""
        expr = RuleExpression(RuleOperator.EQ, "branch_protection_enabled", True)
        rule = Rule(id=..., control_id=..., expression=expr)
        evidence = Evidence.create(repo_id=..., payload={})  # Campo faltante
        
        result = evaluator.evaluate(rule, evidence)
        assert result == EvaluationStatus.UNKNOWN
    
    def test_evaluate_none_evidence(self, evaluator):
        """Test: Sin evidencia → UNKNOWN"""
        expr = RuleExpression(RuleOperator.EQ, "field", "value")
        rule = Rule(id=..., control_id=..., expression=expr)
        
        result = evaluator.evaluate(rule, None)
        assert result == EvaluationStatus.UNKNOWN
    
    def test_evaluate_and_both_true(self, evaluator):
        """Test: AND lógico con ambos verdaderos"""
        left_expr = RuleExpression(RuleOperator.EQ, "required_reviews", 2)
        right_expr = RuleExpression(RuleOperator.EQ, "dismiss_stale", True)
        and_expr = RuleExpression(RuleOperator.AND, left_expr, right_expr)
        
        rule = Rule(id=..., control_id=..., expression=and_expr)
        evidence = Evidence.create(
            repo_id=...,
            payload={"required_reviews": 2, "dismiss_stale": True}
        )
        
        result = evaluator.evaluate(rule, evidence)
        assert result == EvaluationStatus.PASS
    
    def test_reproducibility(self, evaluator):
        """Test: Reproducibilidad → misma entrada, siempre mismo resultado"""
        expr = RuleExpression(RuleOperator.GTE, "required_reviews", 2)
        rule = Rule(id=..., control_id=..., expression=expr)
        evidence = Evidence.create(repo_id=..., payload={"required_reviews": 3})
        
        # Ejecutar 10 veces
        results = [evaluator.evaluate(rule, evidence) for _ in range(10)]
        
        # Todos deben ser PASS
        assert all(r == EvaluationStatus.PASS for r in results)
        # Todos idénticos
        assert len(set(results)) == 1
```

### Ground Truth Dataset

```python
# tests/fixtures/ground_truth_dataset.csv

evidence_id,normalized_payload,expected_status
pass_001,"{""branch_protection_enabled"": true, ""required_reviews"": 2}",PASS
pass_002,"{""branch_protection_enabled"": true, ""required_reviews"": 3}",PASS
...
fail_001,"{""branch_protection_enabled"": false}",FAIL
fail_002,"{""required_reviews"": 0}",FAIL
...
unknown_001,"{""error"": ""403 Forbidden""}",UNKNOWN
unknown_002,"{""error"": ""401 Unauthorized""}",UNKNOWN
...

# Total 100 casos (40 PASS, 40 FAIL, 20 UNKNOWN)
```

### Validación Experimental

```python
# tests/ground_truth_validation.py

import csv
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from app.domain.engine.evaluator import RuleEvaluator

def validate_ground_truth():
    """
    Ejecutar motor contra Ground Truth dataset.
    Calcular métricas: Accuracy, Precision, Recall, F1, matriz confusión.
    """
    
    evaluator = RuleEvaluator()
    
    expected_statuses = []
    predicted_statuses = []
    
    with open("tests/fixtures/ground_truth_dataset.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            evidence_id = row["evidence_id"]
            payload_json = json.loads(row["normalized_payload"])
            expected_status = row["expected_status"]
            
            # Construir rule y evidence
            # (omitido por brevedad)
            evidence = Evidence.create(repo_id=..., payload=payload_json)
            
            # Evaluar
            predicted_status = evaluator.evaluate(rule, evidence).value
            
            expected_statuses.append(expected_status)
            predicted_statuses.append(predicted_status)
    
    # Calcular métricas
    accuracy = accuracy_score(expected_statuses, predicted_statuses)
    precision = precision_score(expected_statuses, predicted_statuses, average='weighted')
    recall = recall_score(expected_statuses, predicted_statuses, average='weighted')
    f1 = f1_score(expected_statuses, predicted_statuses, average='weighted')
    cm = confusion_matrix(expected_statuses, predicted_statuses)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-score: {f1:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    
    # Afirmaciones
    assert accuracy >= 0.95, f"Accuracy {accuracy} < 0.95"
    assert precision >= 0.90, f"Precision {precision} < 0.90"
    assert recall >= 0.90, f"Recall {recall} < 0.90"
    assert f1 >= 0.90, f"F1-score {f1} < 0.90"
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": cm.tolist(),
    }
```

---

## CI/CD Pipeline (GitHub Actions)

### .github/workflows/ci.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [develop]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: securecode_user
          POSTGRES_PASSWORD: password
          POSTGRES_DB: securecode_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Lint with flake8
        run: |
          flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: Format check with black
        run: |
          black --check app tests
      
      - name: Run pytest
        env:
          DATABASE_URL: postgresql://securecode_user:password@localhost:5432/securecode_test
          JWT_SECRET_KEY: test-secret-key-min-32-chars-xxxxxxxx
        run: |
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=html
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
      
      - name: Security check with bandit
        run: |
          bandit -r app -ll -x app/tests
  
  build-and-push:
    needs: lint-and-test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest-${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
  
  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy securecode \
            --image "us-central1-docker.pkg.dev/securecode-mvp/securecode/app:${{ github.sha }}" \
            --region us-central1 \
            --platform managed \
            --set-env-vars DATABASE_URL="${{ secrets.DATABASE_URL }}" \
            --set-env-vars GITHUB_API_TOKEN="${{ secrets.GITHUB_API_TOKEN }}" \
            --set-env-vars JWT_SECRET_KEY="${{ secrets.JWT_SECRET_KEY }}" \
            --allow-unauthenticated
```

---

## Despliegue en Supabase + Cloud Run

> **Costo total: $0** — Supabase Free plan (PostgreSQL 1GB) + Cloud Run Free Tier (2M requests/mes).
> Ver guía completa en: **DEPLOYMENT_SUPABASE_CLOUD_RUN.md**

### Dockerfile (Multistage)

```dockerfile
# Dockerfile — Compatible con Cloud Run (puerto $PORT dinámico)

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache /wheels/*

COPY app/ app/
COPY db/ db/

RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

# Healthcheck (Cloud Run verifica este endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthcheck')" || exit 1

EXPOSE 8000

# Cloud Run inyecta $PORT; usar 8000 como fallback local
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Cloud Run Configuration

```bash
# Deploy a producción (ejecutar una vez o via CI/CD)
gcloud run deploy securecode \
  --image us-central1-docker.pkg.dev/securecode-mvp/securecode/app:latest \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --allow-unauthenticated \
  --set-env-vars APP_ENV="production" \
  --set-env-vars LOG_LEVEL="INFO" \
  --set-env-vars DATABASE_URL="postgresql://postgres:PASSWORD@db.REGION.supabase.co:5432/postgres" \
  --set-env-vars GITHUB_API_TOKEN="ghp_xxxx" \
  --set-env-vars JWT_SECRET_KEY="your-key-min-32-chars"

# Resultado: URL pública
# https://securecode-XXXXX.run.app
```

### Supabase (Base de Datos)

```bash
# 1. Crear proyecto en https://app.supabase.com
#    Plan: Free | Region: us-east-1 | Name: securecode-mvp

# 2. Obtener connection string
# Settings → Database → Connection String → URI
# postgresql://postgres:PASSWORD@db.REGION.supabase.co:5432/postgres

# 3. Ejecutar migraciones (una vez, en Supabase SQL Editor)
alembic upgrade head
# O: Settings → SQL Editor → pegar contenido de 001_init_schema.sql
```

---

## Monitoreo y Observabilidad

### Logging Estructurado

```python
# app/utils/logger.py

import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from app.config import settings

# Setup logging JSON
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# Structured logging helper
def log_event(event_type: str, **kwargs):
    """Log estructurado con contexto"""
    logger.info(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": kwargs,
    }))
```

### Métricas con Prometheus (Optional)

```python
# app/api/middleware/metrics.py

from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request
import time

# Métricas
request_count = Counter(
    'securecode_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'securecode_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

evaluation_count = Counter(
    'securecode_evaluations_total',
    'Total evaluations',
    ['status']  # PASS, FAIL, UNKNOWN
)

async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# Endpoint metrics
@app.get("/metrics")
def metrics():
    return generate_latest()
```

---

## Timeline de Desarrollo

### Hitos y Sprints (85 días hábiles)

| Sprint | Fechas | Hito | Entregables |
|--------|--------|------|-------------|
| **Sprint 1** | 27-Aug a 09-Sep | ES1 Finalizado | Modelo dominio, especificación completa |
| **Sprint 2** | 10-Sep a 20-Sep | Diseño Completo | Esquema BD, APIs definidas, Github spike |
| **Sprint 3** | 21-Sep a 04-Oct | MVP Dev Starter | Persistencia, endpoints básicos, auth |
| **Sprint 4** | 05-Oct a 18-Oct | Motor + Conector | Engine funcional, GitHub connector integrado |
| **Sprint 5** | 19-Oct a 01-Nov | Pruebas + Ground Truth | Unit tests, integration tests, validación experimental |
| **Sprint 6** | 02-Nov a 08-Nov | Despliegue + Docs | Deploy a Cloud Run + Supabase, documentación final |
| **Sprint 7** | 09-Nov a 15-Nov | Demo + Ajustes | Presentación implementación, bug fixes |
| **Sprint 8** | 16-Nov a 22-Nov | Defensa Prep | Ensayo defensa, slides, argumentación |
| **Sprint 9** | 23-Nov a 30-Nov | Buffer | Contingencias, últimos ajustes |
| **Sprint 10** | 01-Dec a 09-Dec | Defensa Final | Presentación oficial |

---

## Checklist de Implementación (MVP Go-Live)

### Jonatthan Medalla (Dominio + Motor)

- [ ] Modelos de dominio DDD completos (Entities, Value Objects)
- [ ] Interfaces de repositorio (Puertos)
- [ ] Motor de reglas determinista (100% reproducibilidad KPI-01)
- [ ] RuleEvaluator con operadores EQ, NEQ, GT, GTE, LT, LTE, AND, OR, IN
- [ ] Unit tests motor (≥85% cobertura)
- [ ] Ground Truth dataset (100 casos: 40 PASS, 40 FAIL, 20 UNKNOWN)
- [ ] Validación experimental (Accuracy ≥95%, Precision/Recall/F1 ≥0.90)
- [ ] Servicio de evaluación (orquestación)
- [ ] Documentación DDD y decisiones arquitectónicas

### Jose Mora (Conector + Infraestructura)

- [ ] Cliente GitHub asincrónico (aiohttp, reintentos, rate limiting)
- [ ] Normalizador GitHub → Esquema canónico
- [ ] Cálculo SHA-256 (reproducible)
- [ ] Persistencia PostgreSQL (SQLAlchemy ORM)
- [ ] Alembic migrations versionadas
- [ ] Endpoints REST (CRUD controls, rules, evaluations)
- [ ] Autenticación JWT (HS256)
- [ ] Dockerfile multistage
- [ ] GitHub Actions CI/CD pipeline
- [ ] Supabase proyecto creado + migraciones ejecutadas
- [ ] Cloud Run deployment exitoso (URL pública verificada)
- [ ] Healthcheck + monitoreo
- [ ] Runbook DRP

### Ambos

- [ ] Tests integración (GitHub client + DB + motor)
- [ ] Load tests (Locust, KPI-03 P95 ≤8s)
- [ ] Security tests (bandit, OWASP)
- [ ] Documentación OpenAPI
- [ ] Informe ES2 completo (Word + anexos)
- [ ] Presentación implementación (slides)
- [ ] Ensayo defensa
- [ ] Go-nogo audit (criterios EA4 cumplidos)

---

## Referencias y Estándares

- **DDD**: Evans, E. (2003). Domain-Driven Design. Addison-Wesley.
- **Hexagonal Architecture**: Cockburn, A. (2005). https://alistair.cockburn.us/hexagonal-architecture/
- **NIST CSF 2.0**: https://doi.org/10.6028/NIST.CSWP.29
- **NIST SP 800-53A**: Evaluation of Controles. https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53Ar5.pdf
- **ITIL v4**: AXELOS (2019). ITIL Foundation.
- **GitHub API v3**: https://docs.github.com/en/rest
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/
- **PostgreSQL 16**: https://www.postgresql.org/docs/16/

---

**Documento Actualizado:** 31 de agosto de 2026  
**Versión:** 2.0 (ES2 Corregido)  
**Estado:** LISTO PARA DESARROLLADORES

