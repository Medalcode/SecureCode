# Requirements Document: SecureCode Core Domain

## Introduction

SecureCode es una plataforma GRC (Governance, Risk, Compliance) para evaluación automática de controles de seguridad. El Core Domain implementa el motor de evaluación de reglas determinista, persistencia de datos en PostgreSQL, y el pipeline de CI/CD para asegurar la calidad del sistema.

Este spec cubre la implementación del MVP que incluye:
- Modelos SQLAlchemy para 8 tablas PostgreSQL
- Motor de reglas determinista (sin efectos secundarios, sin aleatoriedad)
- Tests unitarios con cobertura >85%
- Persistencia inmutable (INSERT ONLY)
- Pipeline CI/CD con GitHub Actions

## Glossary

- **SecureCode**: Plataforma GRC para evaluación automática de controles de seguridad
- **Evidence**: Evidencia recolectada de un repositorio (archivos, configuraciones, metadatos)
- **Rule**: Regla lógica que define cómo evaluar una evidencia (EQ, AND, OR, UNKNOWN)
- **Control**: Controles de seguridad que se pueden evaluar (ej. "code-signing", "two-factor-authentication")
- **Evaluation**: Proceso de aplicar una regla contra una evidencia para determinar PASS/FAIL/UNKNOWN
- **EvaluationResult**: Resultado de una evaluación con status (PASS|FAIL|UNKNOWN) y confidence (0.0-1.0)
- **AuditLog**: Registro inmutable de todas las operaciones críticas
- **GitHubAccount**: Cuenta de GitHub asociada a un usuario
- **Branch**: Rama de repositorio analizada
- **Deterministic Engine**: Motor de evaluación que produce el mismo resultado para los mismos inputs
- **CI Pipeline**: Pipeline de integración continua con linting, unit tests, integration tests

---

## Requirement 1: User Authentication y Autorización

**User Story:** Como desarrollador del sistema, quiero que los usuarios se autentiquen con GitHub OAuth, para que solo usuarios autorizados puedan acceder a la plataforma.

#### Acceptance Criteria

1. WHEN a user visits the login page, THE System SHALL redirect to GitHub OAuth authentication
2. WHEN GitHub returns an authorization code, THE AuthService SHALL exchange it for an access token
3. WHEN a valid OAuth token is received, THE System SHALL create or update a GitHubAccount record
4. IF authentication fails, THEN THE System SHALL return HTTP 401 Unauthorized
5. WHERE OAuth is enabled, THE System SHALL validate ID token signature using GitHub public keys

---

## Requirement 2: Modelo de Datos - Tabla users

**User Story:** Como desarrollador, quiero una tabla users en PostgreSQL para almacenar la información básica de los usuarios registrados, para que el sistema pueda identificar a los usuarios de forma persistente.

#### Acceptance Criteria

1. THE users TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - email (VARCHAR(255), NOT NULL, UNIQUE)
   - name (VARCHAR(255), NOT NULL)
   - avatar_url (VARCHAR(1024), NULL)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
   - updated_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE users TABLE SHALL have an index on email for fast lookup
3. WHEN a user is created, THE System SHALL store the record with created_at timestamp
4. FOR ANY user, IF the email field is updated, THEN the updated_at field SHALL automatically update

---

## Requirement 3: Modelo de Datos - Tabla github_accounts

**User Story:** Como desarrollador, quiero una tabla github_accounts para vincular usuarios de SecureCode con sus cuentas de GitHub, para que el sistema pueda autenticar usuarios mediante OAuth.

#### Acceptance Criteria

1. THE github_accounts TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - user_id (UUID, FOREIGN KEY REFERENCES users(id), NOT NULL, UNIQUE)
   - github_id (BIGINT, NOT NULL, UNIQUE)
   - login (VARCHAR(255), NOT NULL)
   - access_token (VARCHAR(1024), NOT NULL)
   - refresh_token (VARCHAR(1024), NOT NULL)
   - token_expires_at (TIMESTAMP WITH TIME ZONE, NOT NULL)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. WHEN a GitHub account is linked, THE System SHALL store all authentication tokens securely
3. WHEN the access token expires, THE System SHALL use the refresh token to obtain a new access token
4. IF token refresh fails, THEN THE System SHALL invalidate the GitHub account link

---

## Requirement 4: Modelo de Datos - Tabla branches

**User Story:** Como desarrollador, quiero una tabla branches para rastrear qué ramas de qué repositorios han sido analizadas, para que el sistema pueda evitar análisis duplicados.

#### Acceptance Criteria

1. THE branches TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - repository_name (VARCHAR(255), NOT NULL)
   - branch_name (VARCHAR(255), NOT NULL)
   - last_commit_sha (VARCHAR(64), NOT NULL)
   - last_analysis_at (TIMESTAMP WITH TIME ZONE, NULL)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
   - UNIQUE constraint on (repository_name, branch_name)
2. THE branches TABLE SHALL have an index on repository_name for fast filtering
3. WHEN a branch is first analyzed, THE System SHALL store last_analysis_at timestamp
4. WHEN the same repository and branch are analyzed again with a new commit, THE System SHALL create a new record

---

## Requirement 5: Modelo de Datos - Tabla controls

**User Story:** Como desarrollador, quiero una tabla controls para definir qué controles de seguridad pueden ser evaluados, para que el sistema sepa qué reglas aplicar.

#### Acceptance Criteria

1. THE controls TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - name (VARCHAR(255), NOT NULL, UNIQUE)
   - description (TEXT, NOT NULL)
   - category (VARCHAR(100), NOT NULL) -- ej: "code-quality", "security", "compliance"
   - enabled (BOOLEAN, NOT NULL, DEFAULT TRUE)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE controls TABLE SHALL have an index on category for filtering
3. WHEN a control is disabled, THE System SHALL still store it but SHALL NOT evaluate it

---

## Requirement 6: Modelo de Datos - Tabla rules

**User Story:** Como desarrollador, quiero una tabla rules para definir reglas lógicas que evalúan evidencias, para que el sistema pueda aplicar controles de seguridad automáticamente.

#### Acceptance Criteria

1. THE rules TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - control_id (UUID, FOREIGN KEY REFERENCES controls(id), NOT NULL)
   - name (VARCHAR(255), NOT NULL)
   - rule_type (VARCHAR(50), NOT NULL) -- 'EQ', 'AND', 'OR', 'UNKNOWN'
   - expression (TEXT, NOT NULL) -- expresión lógica en formato estructurado
   - parameters (JSONB, NOT NULL) -- parámetros de la regla
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE rules TABLE SHALL enforce that rule_type MUST be one of: 'EQ', 'AND', 'OR', 'UNKNOWN'
3. WHEN a rule is created, THE System SHALL store the rule_type and expression as provided
4. FOR ANY rule, IF rule_type is 'UNKNOWN', THEN parameters MUST include a reason field explaining why UNKNOWN is returned

---

## Requirement 7: Modelo de Datos - Tabla evidences

**User Story:** Como desarrollador, quiero una tabla evidences para almacenar evidencias recolectadas de repositorios, para que el motor de evaluación pueda acceder a ellas.

#### Acceptance Criteria

1. THE evidences TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - branch_id (UUID, FOREIGN KEY REFERENCES branches(id), NOT NULL)
   - evidence_type (VARCHAR(100), NOT NULL) -- 'file', 'metadata', 'config', 'dependency'
   - path (VARCHAR(1024), NOT NULL) -- ruta del archivo o recurso
   - content_hash (CHAR(64), NOT NULL) -- SHA-256 hash del contenido
   - raw_content (TEXT, NULL) -- contenido raw (puede ser NULL para referencias)
   - parsed_data (JSONB, NULL) -- datos parseados (ej: requirements.txt, package.json)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE evidences TABLE SHALL have an index on content_hash for fast duplicate detection
3. WHEN evidence is inserted, THE System SHALL compute and store SHA-256 hash of raw_content
4. IF the same evidence (branch_id, evidence_type, path, content_hash) already exists, THE System SHALL not insert a duplicate

---

## Requirement 8: Modelo de Datos - Tabla evaluations

**User Story:** Como desarrollador, quiero una tabla evaluations para almacenar los resultados de las evaluaciones de reglas contra evidencias, para que los resultados sean persistentes y auditables.

#### Acceptance Criteria

1. THE evaluations TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - evidence_id (UUID, FOREIGN KEY REFERENCES evidences(id), NOT NULL)
   - rule_id (UUID, FOREIGN KEY REFERENCES rules(id), NOT NULL)
   - status (VARCHAR(20), NOT NULL) -- 'PASS', 'FAIL', 'UNKNOWN'
   - confidence (DECIMAL(3,2), NOT NULL) -- 0.00 a 1.00
   - details (TEXT, NULL) -- descripción detallada del resultado
   - evaluated_at (TIMESTAMP WITH TIME ZONE, NOT NULL)
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE evaluations TABLE SHALL have indexes on (evidence_id, rule_id) and (status)
3. WHEN an evaluation is created, THE System SHALL store evaluated_at with current timestamp
4. FOR ANY evaluation, confidence MUST be between 0.00 and 1.00 inclusive
5. WHEN an evaluation with status UNKNOWN is created, THE details field SHALL NOT be NULL

---

## Requirement 9: Modelo de Datos - Tabla audit_logs

**User Story:** Como desarrollador, quiero una tabla audit_logs para registrar todas las operaciones críticas del sistema, para que haya trazabilidad completa de las acciones.

#### Acceptance Criteria

1. THE audit_logs TABLE SHALL have the following columns:
   - id (UUID, PRIMARY KEY, NOT NULL)
   - event_type (VARCHAR(100), NOT NULL) -- 'EVALUATION_STARTED', 'EVALUATION_COMPLETED', 'RULE_APPLIED', etc.
   - resource_type (VARCHAR(50), NOT NULL) -- 'EVIDENCE', 'RULE', 'EVALUATION'
   - resource_id (UUID, NOT NULL)
   - user_id (UUID, NULL) -- NULL if system operation
   - metadata (JSONB, NOT NULL) -- datos adicionales del evento
   - created_at (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())
2. THE audit_logs TABLE SHALL have indexes on (event_type, created_at) and (resource_type, resource_id)
3. WHEN any evaluation completes, THE System SHALL create an audit_log with event_type EVALUATION_COMPLETED
4. FOR ANY audit_log entry, the metadata field SHALL include the execution context

---

## Requirement 10: Motor de Reglas Determinista - Evaluación Básica

**User Story:** Como desarrollador, quiero que el motor de reglas evalúe reglas EQ, AND, OR contra evidencias de forma determinista, para que siempre obtenga el mismo resultado para los mismos inputs.

#### Acceptance Criteria

1. WHEN the RuleEngine receives an evidence and a rule, THE Engine SHALL return an EvaluationResult
2. WHEN the rule type is 'EQ', THE Engine SHALL compare evidence fields against expected values
3. WHEN the rule type is 'AND', THE Engine SHALL evaluate ALL conditions and return PASS only if ALL are PASS
4. WHEN the rule type is 'OR', THE Engine SHALL evaluate conditions and return PASS if AT LEAST ONE is PASS
5. WHEN all conditions are evaluated, THE Engine SHALL compute confidence as the ratio of PASS conditions to total conditions
6. FOR ANY evaluation, IF the result is UNKNOWN, THE Engine SHALL include a reason in the details field

---

## Requirement 11: Motor de Reglas Determinista - Sin Efectos Secundarios

**User Story:** Como desarrollador, quiero que el motor de reglas sea 100% determinista sin efectos secundarios, para que sea predecible y reproducible.

#### Acceptance Criteria

1. WHEN the RuleEngine evaluates a rule, THE Engine SHALL NOT call datetime.now() or any time-based function
2. WHEN the RuleEngine evaluates a rule, THE Engine SHALL NOT call random() or any randomness function
3. WHEN the RuleEngine evaluates a rule, THE Engine SHALL NOT make network calls or file I/O
4. FOR ANY two executions with identical inputs, THE RuleEngine SHALL produce identical outputs
5. IF 100 executions are performed with the same inputs, THE System SHALL return 100 identical results

---

## Requirement 12: Motor de Reglas Determinista - Estado Desconocido (UNKNOWN)

**User Story:** Como desarrollador, quiero que el motor de reglas pueda retornar UNKNOWN cuando no hay suficiente información, para que el sistema no falso-publique resultados inciertos.

#### Acceptance Criteria

1. WHEN a rule cannot be evaluated due to missing evidence, THE Engine SHALL return UNKNOWN status
2. WHEN the rule type is 'UNKNOWN', THE Engine SHALL return UNKNOWN status with reason from rule parameters
3. WHEN UNKNOWN is returned, THE Engine SHALL include a detailed reason in the details field
4. FOR ANY UNKNOWN result, THE confidence field SHALL be 0.00

---

## Requirement 13: Persistencia PostgreSQL - Inmutable (INSERT ONLY)

**User Story:** Como desarrollador, quiero que las tablas críticas sean inmutables (INSERT ONLY), para que no se pierda trazabilidad histórica.

#### Acceptance Criteria

1. FOR ANY evidence INSERT, THE System SHALL NOT UPDATE or DELETE the record
2. FOR ANY evaluation INSERT, THE System SHALL NOT UPDATE or DELETE the record
3. FOR ANY audit_log INSERT, THE System SHALL NOT UPDATE or DELETE the record
4. WHEN a new version of evidence is needed, THE System SHALL create a new record with a new UUID
5. THE System SHALL allow SELECT queries but SHALL NOT support UPDATE or DELETE operations on critical tables

---

## Requirement 14: Persistencia PostgreSQL - Optimización

**User Story:** Como desarrollador, quiero que las tablas estén optimizadas con índices y constraints, para que las consultas sean rápidas y los datos integros.

#### Acceptance Criteria

1. ALL foreign key relationships SHALL be enforced with FOREIGN KEY constraints
2. ALL unique fields SHALL have UNIQUE constraints
3. THE evidences TABLE SHALL have an index on content_hash (SHA-256)
4. THE evaluations TABLE SHALL have an index on (evidence_id, rule_id) for fast lookups
5. ALL timestamp fields SHALL use TIMESTAMP WITH TIME ZONE for consistency

---

## Requirement 15: Tests Unitarios - Cobertura

**User Story:** Como desarrollador, quiero tests unitarios con cobertura >85% del motor de reglas, para que tenga confianza en que el sistema funciona correctamente.

#### Acceptance Criteria

1. THE test suite SHALL cover all rule types: EQ, AND, OR, UNKNOWN
2. WHEN running tests, THE coverage report SHALL show >85% coverage of the rule engine code
3. THE test suite SHALL include tests for reproducibility (10 ejecuciones idénticas)
4. THE test suite SHALL verify NO random() or datetime.now() calls in the rule engine
5. WHEN tests are run, THE System SHALL fail if coverage < 85%

---

## Requirement 16: Tests Unitarios - Casos de Prueba Específicos

**User Story:** Como desarrollador, quiero tests unitarios específicos para casos críticos, para que los errores se detecten temprano.

#### Acceptance Criteria

1. WHEN the input is a valid rule with all PASS conditions, THE output SHALL have status PASS and confidence 1.00
2. WHEN the input is a rule with some FAIL conditions, THE output SHALL have status FAIL and confidence < 1.00
3. WHEN the input is a rule with all FAIL conditions, THE output SHALL have status FAIL and confidence 0.00
4. WHEN the input is a rule with UNKNOWN type, THE output SHALL have status UNKNOWN and confidence 0.00
5. WHEN evidence is missing or malformed, THE output SHALL return UNKNOWN with reason in details

---

## Requirement 17: Tests Unitarios - Reproducibilidad

**User Story:** Como desarrollador, quiero verificar que el motor de reglas sea 100% reproducible, para que no haya comportamientos inconsistentes.

#### Acceptance Criteria

1. WHEN the same evidence and rule are evaluated 10 times, THE System SHALL return identical results each time
2. WHEN the same evidence and rule are evaluated 100 times, THE System SHALL return identical results each time
3. FOR ANY evaluation, IF the rule and evidence are unchanged, THE result SHALL be identical across runs
4. THE test suite SHALL include a test that performs 100 evaluations and verifies all results are identical

---

## Requirement 18: Tests Unitarios - No Randomness

**User Story:** Como desarrollador, quiero que el motor de reglas no use aleatoriedad, para que sea predecible.

#### Acceptance Criteria

1. WHEN the RuleEngine is analyzed, THE code SHALL NOT contain any calls to random(), random.randint(), np.random, or similar
2. WHEN tests run, THE System SHALL detect any random() calls and FAIL the test
3. FOR ANY execution path in the rule engine, THE output MUST be fully determined by the inputs

---

## Requirement 19: Tests Unitarios - No Datetime

**User Story:** Como desarrollador, quiero que el motor de reglas no use datetime.now(), para que sea determinista.

#### Acceptance Criteria

1. WHEN the RuleEngine is analyzed, THE code SHALL NOT contain any calls to datetime.now(), time.time(), or similar
2. WHEN tests run, THE System SHALL detect any datetime.now() calls and FAIL the test
3. FOR ANY evaluation, THE evaluated_at timestamp SHALL be provided as input, not computed

---

## Requirement 20: CI Pipeline - GitHub Actions

**User Story:** Como desarrollador, quiero un pipeline CI con GitHub Actions para validar código antes de merge, para que la calidad se mantenga alta.

#### Acceptance Criteria

1. WHEN code is pushed to any branch, THE CI SHALL run linting with flake8
2. WHEN linting completes successfully, THE CI SHALL run unit tests
3. WHEN unit tests complete, THE CI SHALL generate a coverage report
4. IF coverage < 85%, THE CI SHALL fail the pipeline
5. WHEN all checks pass, THE CI SHALL allow the pull request to be merged

---

## Requirement 21: CI Pipeline - Jobs Secuenciales

**User Story:** Como desarrollador, quiero que los jobs del CI se ejecuten en secuencia, para que errores se detecten temprano.

#### Acceptance Criteria

1. THE CI pipeline SHALL have three jobs in order: lint → unit tests → integration tests
2. WHEN linting fails, THE CI SHALL NOT run unit tests
3. WHEN unit tests fail, THE CI SHALL NOT run integration tests
4. WHEN any job fails, THE CI SHALL mark the entire run as failed

---

## Requirement 22: CI Pipeline - Linting (flake8)

**User Story:** Como desarrollador, quiero linting con flake8 para detectar errores de estilo y buenas prácticas, para que el código sea consistente.

#### Acceptance Criteria

1. THE lint job SHALL run flake8 on all Python files
2. WHEN flake8 finds violations, THE CI SHALL fail with exit code 1
3. WHEN flake8 passes, THE CI SHALL proceed to unit tests
4. THE lint job SHALL use the flake8 configuration from .flake8 file

---

## Requirement 23: CI Pipeline - Unit Tests

**User Story:** Como desarrollador, quiero unit tests que verifiquen el motor de reglas y persistencia, para que los errores se detecten temprano.

#### Acceptance Criteria

1. THE unit tests job SHALL run pytest with the test suite
2. WHEN any test fails, THE CI SHALL fail with exit code 1
3. WHEN all tests pass, THE CI SHALL generate a coverage report
4. THE unit tests job SHALL require >85% coverage to pass

---

## Requirement 24: CI Pipeline - Integration Tests

**User Story:** Como desarrollador, quiero integration tests que verifiquen la persistencia y flujo completo, para que el sistema sea confiable.

#### Acceptance Criteria

1. THE integration tests job SHALL test evidence storage and retrieval
2. WHEN an evidence is inserted, THE System SHALL verify it can be retrieved by hash
3. WHEN an evaluation is created, THE System SHALL verify it persists correctly
4. WHEN audit logging is enabled, THE System SHALL verify audit_log entries are created

---

## Requirement 25: CI Pipeline - Feedback

**User Story:** Como desarrollador, quiero feedback claro de los fallos de CI, para que los errores sean fáciles de corregir.

#### Acceptance Criteria

1. WHEN a linting failure occurs, THE CI SHALL output the specific flake8 violation messages
2. WHEN a test failure occurs, THE CI SHALL output the test name and failure details
3. WHEN coverage < 85%, THE CI SHALL output the coverage percentage and missing lines
4. WHEN any job fails, THE CI SHALL provide a link to the full log output

---

## Requirement 26: Modelos SQLAlchemy - Definición Completa

**User Story:** Como desarrollador, quiero que todos los modelos SQLAlchemy estén definidos en un solo lugar, para que la estructura de datos sea mantenible.

#### Acceptance Criteria

1. ALL 8 models (users, github_accounts, branches, controls, rules, evidences, evaluations, audit_logs) SHALL be defined in src/models/
2. EACH model SHALL have proper SQLAlchemy Column definitions with types
3. EACH model SHALL have relationships defined with relationship()
4. WHEN models are imported, THE System SHALL create all tables if they don't exist
5. FOR ANY model, the __tablename__ attribute SHALL be set to the correct table name

---

## Requirement 27: Motor de Reglas - Evaluación Completa

**User Story:** Como desarrollador, quiero que el motor de reglas soporte todas las operaciones lógicas (EQ, AND, OR, UNKNOWN), para que pueda evaluar cualquier regla.

#### Acceptance Criteria

1. WHEN a rule with type 'EQ' is evaluated, THE Engine SHALL compare fields and return PASS/FAIL
2. WHEN a rule with type 'AND' is evaluated, THE Engine SHALL require ALL conditions to PASS
3. WHEN a rule with type 'OR' is evaluated, THE Engine SHALL require AT LEAST ONE condition to PASS
4. WHEN a rule with type 'UNKNOWN' is evaluated, THE Engine SHALL return UNKNOWN with reason
5. FOR ANY rule evaluation, THE confidence field SHALL be calculated as PASS/total ratio

---

## Requirement 28: Persistencia PostgreSQL - Pruebas de Integridad

**User Story:** Como desarrollador, quiero que las pruebas de persistencia verifiquen integridad de datos, para que no haya corrupción.

#### Acceptance Criteria

1. WHEN 100 evidences are inserted, THE System SHALL verify all 100 records exist in database
2. WHEN an evidence is inserted with same hash as existing, THE System SHALL not insert duplicate
3. WHEN an evaluation is created, THE System SHALL verify it can be retrieved by ID
4. FOR ANY audit_log entry, THE System SHALL verify it can be queried by event_type

---

## Requirement 29: Integración entre Componentes

**User Story:** Como desarrollador, quiero que el motor de reglas se integre con la persistencia, para que los resultados se guarden correctamente.

#### Acceptance Criteria

1. WHEN the RuleEngine evaluates an evidence, THE System SHALL store the evaluation in the evaluations table
2. WHEN an evaluation is stored, THE System SHALL create an audit_log entry with EVALUATION_COMPLETED event
3. WHEN multiple rules are evaluated against the same evidence, THE System SHALL store each evaluation separately
4. FOR ANY evaluation, THE System SHALL link it to the evidence and rule via foreign keys

---

## Requirement 30: Arquitectura del Sistema

**User Story:** Como desarrollador, quiero que el sistema tenga una arquitectura limpia separando concerns, para que sea mantenible y testable.

#### Acceptance Criteria

1. THE System SHALL have separate modules for models, engine, persistence, and tests
2. WHEN the RuleEngine is tested, THE System SHALL use mocks instead of real database connections
3. WHEN persistence is tested, THE System SHALL use a test database
4. FOR ANY module, dependencies SHALL be injected rather than hardcoded

---

## Requirement 31: Documentación de Código

**User Story:** Como desarrollador, quiero que el código esté bien documentado, para que otros desarrolladores puedan entenderlo.

#### Acceptance Criteria

1. ALL public functions SHALL have docstrings explaining purpose, parameters, and return values
2. ALL classes SHALL have class docstrings explaining responsibility
3. COMPLEX logic in the RuleEngine SHALL have inline comments explaining reasoning
4. THE README SHALL document how to run the system locally and in production

---

## Requirement 32: Configuración del Sistema

**User Story:** Como desarrollador, quiero que la configuración sea manejada mediante variables de entorno, para que puedan variar entre entornos.

#### Acceptance Criteria

1. WHEN the application starts, THE System SHALL load configuration from environment variables
2. THE Database URL SHALL be configurable via DATABASE_URL environment variable
3. WHEN DATABASE_URL is not set, THE System SHALL fail to start with clear error message
4. ALL secrets (tokens, passwords) SHALL be loaded from environment variables, not hardcoded

---

## Requirement 33: Manejo de Errores

**User Story:** Como desarrollador, quiero que los errores sean manejados de forma consistente, para que el sistema sea robusto.

#### Acceptance Criteria

1. WHEN a database connection fails, THE System SHALL raise a DatabaseConnectionError
2. WHEN a rule evaluation fails, THE System SHALL return UNKNOWN with error details
3. WHEN invalid input is provided, THE System SHALL raise a ValidationError with specific message
4. FOR ANY error, THE System SHALL log the error to audit_logs with ERROR event_type

---

## Requirement 34: Performance del Motor de Reglas

**User Story:** Como desarrollador, quiero que el motor de reglas sea eficiente, para que no sea un cuello de botella.

#### Acceptance Criteria

1. WHEN evaluating 100 evidences against 10 rules, THE System SHALL complete in < 5 seconds
2. WHEN evaluating a single evidence against a rule, THE System SHALL complete in < 50ms
3. FOR ANY evaluation, THE System SHALL cache computed results if inputs haven't changed
4. WHEN the same evidence is evaluated multiple times, THE System SHALL use cached results

---

## Requirement 35: Escalabilidad

**User Story:** Como desarrollador, quiero que el sistema pueda escalar horizontalmente, para que maneje más carga.

#### Acceptance Criteria

1. WHEN multiple instances of the RuleEngine run, THE System SHALL return identical results for same inputs
2. WHEN database connections are made, THE System SHALL use connection pooling
3. FOR ANY stateful operation, THE System SHALL store state in PostgreSQL, not in memory
4. WHEN the system is deployed to Cloud Run, THE System SHALL scale to zero when idle
