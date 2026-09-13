# SECURECODE — Comprehensive Testing Guide

**Documento:** Guía exhaustiva de pruebas y validación  
**Versión:** 1.0  
**Fecha:** 31 de agosto de 2026

---

## 🎯 Estrategia de Testing

SECURECODE utiliza una pirámide de testing:

```
        /\
       /  \        E2E (Smoke tests)        [10%]
      /----\
     /      \      Integration tests        [30%]
    /--------\
   /          \    Unit tests               [60%]
  /____________\
```

**Cobertura Target:** ≥85% líneas, ≥75% ramas

---

## 1. Unit Tests (Motor de Reglas)

### Objetivo
Validar reproducibilidad y determinismo del motor en aislamiento.

### Setup
```bash
pytest tests/unit/ -v --cov=app.domain.engine
```

### Test Suite: Motor (app/domain/engine/evaluator.py)

```python
# tests/unit/test_engine_evaluator.py

class TestRuleEvaluator:
    """Suite: Motor de reglas determinista"""
    
    def test_evaluate_eq_pass(self):
        """PASS: campo == valor esperado"""
        # Given
        expr = RuleExpression(RuleOperator.EQ, "field", "value")
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"field": "value"})
        
        # When
        result = RuleEvaluator().evaluate(rule, evidence)
        
        # Then
        assert result == EvaluationStatus.PASS
    
    def test_evaluate_eq_fail(self):
        """FAIL: campo != valor esperado"""
        expr = RuleExpression(RuleOperator.EQ, "field", "expected")
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"field": "actual"})
        
        result = RuleEvaluator().evaluate(rule, evidence)
        
        assert result == EvaluationStatus.FAIL
    
    def test_evaluate_missing_field(self):
        """UNKNOWN: campo requerido no presente"""
        expr = RuleExpression(RuleOperator.EQ, "missing_field", "value")
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={})
        
        result = RuleEvaluator().evaluate(rule, evidence)
        
        assert result == EvaluationStatus.UNKNOWN
    
    def test_evaluate_no_evidence(self):
        """UNKNOWN: sin evidencia"""
        expr = RuleExpression(RuleOperator.EQ, "field", "value")
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        
        result = RuleEvaluator().evaluate(rule, None)
        
        assert result == EvaluationStatus.UNKNOWN
    
    def test_reproducibility_10x(self):
        """PASS: 10 re-evaluaciones producen mismo resultado (reproducibilidad)"""
        expr = RuleExpression(RuleOperator.GTE, "count", 5)
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"count": 10})
        
        evaluator = RuleEvaluator()
        results = [evaluator.evaluate(rule, evidence) for _ in range(10)]
        
        # Todos deben ser idénticos
        assert all(r == EvaluationStatus.PASS for r in results)
        assert len(set(results)) == 1  # Solo un valor único
    
    def test_and_operator_both_true(self):
        """PASS: AND con ambas condiciones verdaderas"""
        left = RuleExpression(RuleOperator.EQ, "a", 1)
        right = RuleExpression(RuleOperator.EQ, "b", 2)
        expr = RuleExpression(RuleOperator.AND, left, right)
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"a": 1, "b": 2})
        
        result = RuleEvaluator().evaluate(rule, evidence)
        
        assert result == EvaluationStatus.PASS
    
    def test_and_operator_one_false(self):
        """FAIL: AND con una condición falsa"""
        left = RuleExpression(RuleOperator.EQ, "a", 1)
        right = RuleExpression(RuleOperator.EQ, "b", 999)
        expr = RuleExpression(RuleOperator.AND, left, right)
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"a": 1, "b": 2})
        
        result = RuleEvaluator().evaluate(rule, evidence)
        
        assert result == EvaluationStatus.FAIL
    
    def test_or_operator_one_true(self):
        """PASS: OR con una condición verdadera"""
        left = RuleExpression(RuleOperator.EQ, "a", 999)
        right = RuleExpression(RuleOperator.EQ, "b", 2)
        expr = RuleExpression(RuleOperator.OR, left, right)
        rule = Rule(id=uuid4(), control_id=uuid4(), expression=expr)
        evidence = Evidence.create(repo_id=uuid4(), payload={"a": 1, "b": 2})
        
        result = RuleEvaluator().evaluate(rule, evidence)
        
        assert result == EvaluationStatus.PASS
    
    def test_no_random_in_engine(self):
        """PASS: Engine no depende de random()"""
        # Verificar que no hay random() en el código del motor
        import inspect
        source = inspect.getsource(RuleEvaluator)
        assert "random" not in source.lower()
    
    def test_no_datetime_in_engine(self):
        """PASS: Engine no depende de datetime.now()"""
        import inspect
        source = inspect.getsource(RuleEvaluator)
        assert "datetime.now()" not in source
        assert "time.time()" not in source
```

---

## 2. Integration Tests (GitHub + DB + Motor)

### Objetivo
Validar flujo completo: GitHub → Normalización → DB → Evaluación.

### Setup
```bash
pytest tests/integration/ -v --cov=app
```

### Test Suite: GitHub Client

```python
# tests/integration/test_github_client.py

@pytest.mark.asyncio
class TestGitHubClient:
    """Suite: Integración con GitHub API"""
    
    @pytest.fixture
    async def client(self):
        """Fixture: Cliente GitHub con token válido"""
        token = os.getenv("GITHUB_API_TOKEN")
        client = GitHubClient(token)
        yield client
        await client.close()
    
    async def test_get_branch_protection_success(self, client):
        """PASS: Obtener branch protection de repo válido"""
        # Using a public test repo
        payload = await client.get_branch_protection(
            owner="github",
            repo="hello-world",
            branch="master"
        )
        
        assert isinstance(payload, dict)
        assert "protected" in payload
    
    async def test_get_branch_protection_not_found(self, client):
        """FAIL: Repo no existe"""
        with pytest.raises(GitHubError):
            await client.get_branch_protection(
                owner="nonexistent-org-12345",
                repo="nonexistent-repo",
                branch="main"
            )
    
    async def test_retry_on_rate_limit(self, client, mocker):
        """PASS: Reintenta en 429 con backoff exponencial"""
        # Mock respuesta 429 (rate limit)
        responses = [
            aiohttp.web.Response(status=429, headers={"Retry-After": "1"}),
            aiohttp.web.Response(status=200, text='{"protected": true}'),
        ]
        
        # Implementar mock...
        # Verificar que se reintentan 3 veces máximo
```

### Test Suite: Persistencia

```python
# tests/integration/test_persistence.py

@pytest.mark.asyncio
class TestPersistence:
    """Suite: Base de datos PostgreSQL"""
    
    @pytest.fixture
    async def db_session(self):
        """Fixture: Sesión DB para tests"""
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with AsyncSessionLocal() as session:
            yield session
        
        # Cleanup
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def test_persist_evaluation(self, db_session):
        """PASS: Persistir evaluación inmutable"""
        # Create
        evaluation = Evaluation(
            id=uuid4(),
            rule_id=uuid4(),
            evidence_id=uuid4(),
            status=EvaluationStatus.PASS,
            evaluated_at=datetime.utcnow(),
            evidence_hash_at_time="abc123"
        )
        
        db_session.add(evaluation)
        await db_session.commit()
        
        # Read
        result = await db_session.get(Evaluation, evaluation.id)
        assert result.status == EvaluationStatus.PASS
        assert result.evidence_hash_at_time == "abc123"
    
    async def test_evaluation_immutable(self, db_session):
        """FAIL: No permitir UPDATE en evaluations"""
        # Create
        evaluation = Evaluation(...)
        db_session.add(evaluation)
        await db_session.commit()
        
        # Intentar UPDATE
        evaluation.status = EvaluationStatus.FAIL
        
        with pytest.raises(Exception):  # DB constraint violation
            await db_session.commit()
```

---

## 3. Load Tests (Locust)

### Objetivo
Validar KPI-03: Latencia P95 ≤ 3s bajo 100 usuarios concurrentes.

### Setup
```bash
# Instalar Locust
pip install locust

# Ejecutar tests
locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 300
```

### Load Test: Evaluations bajo presión

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between
import json

class EvaluationUser(HttpUser):
    """Simular usuario que ejecuta evaluaciones"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login al inicio"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@securecode.local", "password": "admin123"}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(5)  # 5x más frecuente que otras tareas
    def execute_evaluation(self):
        """Ejecutar evaluación (tarea pesada)"""
        self.client.post(
            "/api/v1/evaluations",
            json={"rule_id": "...", "repository_id": "..."},
            headers=self.headers,
            name="/api/v1/evaluations"
        )
    
    @task(3)
    def get_report(self):
        """Obtener reporte"""
        self.client.get(
            "/api/v1/reports/compliance",
            headers=self.headers,
            name="/api/v1/reports/compliance"
        )
    
    @task(1)
    def list_controls(self):
        """Listar controles"""
        self.client.get(
            "/api/v1/controls",
            headers=self.headers,
            name="/api/v1/controls"
        )

# Métricas esperadas:
# - Response time P95: ≤ 3 segundos
# - Response time P99: ≤ 8 segundos
# - Error rate: < 1%
# - Throughput: ≥ 50 req/sec
```

---

## 4. Ground Truth Validation

### Objetivo
Validar exactitud del motor contra 100 casos etiquetados.

### Dataset (100 casos)

```csv
# tests/fixtures/ground_truth_dataset.csv
evidence_id,control_code,payload_json,expected_status,rule_id
pass_001,GH-001,"{""field"": true}",PASS,rule-001
fail_001,GH-001,"{""field"": false}",FAIL,rule-001
unknown_001,GH-001,"{""error"": ""403""}",UNKNOWN,rule-001
```

### Validación Script

```python
# tests/ground_truth_validation.py

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def test_ground_truth_accuracy():
    """Validar Accuracy ≥ 95% en Ground Truth"""
    
    dataset = load_csv("tests/fixtures/ground_truth_dataset.csv")
    evaluator = RuleEvaluator()
    
    expected = []
    predicted = []
    
    for row in dataset:
        evidence = Evidence.from_json(row["payload_json"])
        rule = load_rule(row["rule_id"])
        
        status = evaluator.evaluate(rule, evidence)
        
        expected.append(row["expected_status"])
        predicted.append(status)
    
    accuracy = accuracy_score(expected, predicted)
    assert accuracy >= 0.95, f"Accuracy {accuracy} < 0.95"
    
    # Precisión por clase
    for status in ["PASS", "FAIL", "UNKNOWN"]:
        precision = precision_score(expected, predicted, labels=[status], average=None)[0]
        assert precision >= 0.90, f"Precision {status}: {precision} < 0.90"

def test_ground_truth_recall():
    """Validar Recall (Sensibilidad) ≥ 90%"""
    # Similar a test_ground_truth_accuracy
    
    for status in ["PASS", "FAIL", "UNKNOWN"]:
        recall = recall_score(expected, predicted, labels=[status], average=None)[0]
        assert recall >= 0.90, f"Recall {status}: {recall} < 0.90"

def test_confusion_matrix():
    """Generar matriz confusión para auditoria"""
    cm = confusion_matrix(expected, predicted)
    
    print("\nConfusion Matrix:")
    print(cm)
    print("\nPrecision/Recall por clase:")
    for i, status in enumerate(["PASS", "FAIL", "UNKNOWN"]):
        precision = cm[i,i] / cm[:,i].sum()
        recall = cm[i,i] / cm[i,:].sum()
        print(f"{status}: P={precision:.2f}, R={recall:.2f}")
```

---

## 5. Security Tests

### Objetivo
Validar defensa contra OWASP Top 10, inyección SQL, secrets en código.

### Setup
```bash
bandit -r app -ll
```

### Test Suite

```python
# tests/security/test_security.py

def test_no_secrets_in_code():
    """FAIL: Detectar hardcoded secrets"""
    # Buscar patrones de tokens
    patterns = [
        r"ghp_[a-zA-Z0-9]{36,}",  # GitHub tokens
        r"eyJ[A-Za-z0-9_-]+",      # JWTs
    ]
    
    for pattern in patterns:
        matches = find_in_codebase(pattern)
        assert not matches, f"Secrets found: {matches}"

def test_password_hashing_argon2():
    """PASS: Contraseñas hasheadas con Argon2"""
    from app.adapters.auth.jwt_handler import JWTHandler
    
    plain = "test_password_12345"
    hashed = JWTHandler.hash_password(plain)
    
    # Verificar
    assert JWTHandler.verify_password(plain, hashed)
    assert JWTHandler.verify_password("wrong_password", hashed) == False
    
    # Argon2 ≠ plaintext
    assert hashed != plain
    assert len(hashed) > 50  # Argon2 es largo

def test_jwt_signature_verification():
    """PASS: JWT debe tener firma válida"""
    token = JWTHandler.create_access_token("test@example.com")
    
    # Verificar con key correcto
    payload = JWTHandler.verify_token(token)
    assert payload.sub == "test@example.com"
    
    # Falla con key incorrecto
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, "wrong_key", algorithms=["HS256"])

def test_sql_injection_prevention():
    """PASS: Queries parametrizadas (SQLAlchemy ORM)"""
    # Intentar inyección
    malicious = "'; DROP TABLE users; --"
    
    # SQLAlchemy previene inyección
    result = db_session.query(User).filter(User.email == malicious).first()
    assert result is None  # No ejecuta SQL peligroso
```

---

## 6. Performance Benchmarks

### Objetivo
Validar que operaciones críticas cumplen SLAs.

```python
# tests/performance/test_benchmarks.py

def test_motor_latency(benchmark):
    """Motor debe procesar en <100ms por evaluación"""
    rule = create_test_rule()
    evidence = create_test_evidence()
    evaluator = RuleEvaluator()
    
    result = benchmark(lambda: evaluator.evaluate(rule, evidence))
    
    assert result in [EvaluationStatus.PASS, EvaluationStatus.FAIL, EvaluationStatus.UNKNOWN]

def test_sha256_hash_performance(benchmark):
    """Hash SHA-256 debe procesarse en <10ms"""
    payload = {"key": "value" * 100}
    
    result = benchmark(lambda: GitHubNormalizer.calculate_hash(payload))
    
    assert len(result) == 64  # SHA-256 es 64 caracteres hex
```

---

## 7. Running All Tests

### Command Summary

```bash
# Tests unitarios solamente
make test-unit

# Tests integración solamente
make test-int

# Validación Ground Truth
make test-gt

# Load testing con Locust
make load-test

# Security checks
make security-check

# All tests with coverage
make test

# Pre-commit checks (lint + format + test)
make all
```

### CI/CD Integration (GitHub Actions)

```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ -v --cov=app
      - run: bandit -r app -ll
```

---

## 8. KPI Validation Checklist

**Antes de ES2 submission:**

- [ ] KPI-01 Reproducibilidad: test_reproducibility_10x pasa
- [ ] KPI-02 Cobertura: ≥90% controles con regla activa
- [ ] KPI-03 Latencia: Load test P95 ≤ 3s, P99 ≤ 8s
- [ ] KPI-04 UNKNOWN: Ground Truth detection ≥95%
- [ ] Accuracy: Ground Truth ≥95%
- [ ] Precision: Todas clases ≥0.90
- [ ] Recall: Todas clases ≥0.90
- [ ] F1-score: Todas clases ≥0.90
- [ ] Code Coverage: ≥85%
- [ ] Security: bandit zero HIGH/CRITICAL

