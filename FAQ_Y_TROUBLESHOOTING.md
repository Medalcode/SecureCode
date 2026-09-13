# SECURECODE — FAQ y Troubleshooting Avanzado

**Documento:** Preguntas frecuentes y solución de problemas  
**Versión:** 1.0  
**Fecha:** 31 de agosto de 2026

---

## ❓ PREGUNTAS FRECUENTES (FAQ)

### 1. ¿Cuál es la diferencia entre PASS, FAIL y UNKNOWN?

**PASS:** La evidencia obtenida satisface completamente la regla evaluada.
```
Ejemplo: Regla es "branch_protection_enabled == true"
         Evidencia es {"branch_protection_enabled": true}
         Resultado: PASS ✓
```

**FAIL:** La evidencia demuestra que el control NO se cumple.
```
Ejemplo: Regla es "branch_protection_enabled == true"
         Evidencia es {"branch_protection_enabled": false}
         Resultado: FAIL ✗
```

**UNKNOWN:** No hay evidencia suficiente para decidir (no es incumplimiento).
```
Ejemplo: Regla es "branch_protection_enabled == true"
         Evidencia es {} (campo faltante)
         Resultado: UNKNOWN ❓
```

**Por qué esto importa:**
- FAIL definitivo: el control está roto, requiere acción inmediata
- UNKNOWN: probablemente falta configurar o la API no respondió, investigar
- NO asumimos "sin datos = incumplimiento" (eso es peligroso)

---

### 2. ¿Por qué el motor no usa random() o datetime.now()?

Necesitamos **reproducibilidad 100%**: misma entrada → siempre mismo resultado.

Si el motor usara `random()`:
```python
# ❌ MAL
if random.random() > 0.5:
    return EvaluationStatus.PASS
else:
    return EvaluationStatus.FAIL
# Misma evidencia, distintos resultados cada vez
```

El motor es una **función pura**:
```python
# ✓ BIEN
def evaluate(rule: Rule, evidence: Optional[Evidence]) -> EvaluationStatus:
    # Sin dependencias externas (random, time, file system, network)
    # Sin state que cambie entre llamadas
    # Determinista: f(x) siempre = mismo resultado
```

Validamos con:
- `test_reproducibility_10x`: 10 evaluaciones = mismo resultado
- Ground Truth dataset: 100 casos conocidos, Accuracy ≥95%

---

### 3. ¿Por qué PostgreSQL y no SQLite?

| Aspecto | SQLite | PostgreSQL |
|--------|--------|-----------|
| ACID serializables | ❌ No | ✅ Sí |
| Concurrencia multiusuario | ❌ Limitada (readers-writer lock) | ✅ Excelente (MVCC) |
| JSONB indexable | ❌ No | ✅ Sí (GIN, GIST) |
| Integridad referencial | ✅ Sí (con PRAGMA) | ✅ Sí |
| Backups automáticos | ❌ Archivo | ✅ PITR, snapshots |
| Auditoría native | ❌ No | ✅ audit_logs fácil |

**Para GRC (compliance), necesitamos:**
- Transacciones serializables → PostgreSQL
- Evaluaciones inmutables (append-only) → PostgreSQL constraints
- Queries complejas en JSONB → PostgreSQL

---

### 4. ¿Qué pasa si GitHub API está caída?

Tres capas de defensa:

**Capa 1: Reintentos exponenciales**
```python
# 1er intento: falla con 500
# Espera 1s, 2º intento: falla con 503
# Espera 2s, 3er intento: falla con 503
# Espera 4s, 4º intento: FAIL, marca UNKNOWN
```

**Capa 2: Fallback a datos anteriores**
```python
# Si ingesta falla hoy, usamos evidencia de ayer
# Mejor: datos viejos que: decidir sin datos
```

**Capa 3: Explícito UNKNOWN**
```python
# No evaluamos si no hay evidencia
# Resultado: UNKNOWN (no decimos que incumple)
# Admin sabe que requiere investigación
```

**SLA Compromiso:**
- RTO (Recovery Time Objective): < 30 minutos
- RPO (Recovery Point Objective): < 24 horas

---

### 5. ¿Cómo se garantiza seguridad del token GitHub?

**Almacenamiento:**
```bash
# ❌ NUNCA hardcoded
GITHUB_API_TOKEN = "ghp_xxxx"  # En código

# ✓ SIEMPRE en variables de entorno
GITHUB_API_TOKEN=$(cat .env)  # O variables de entorno Cloud Run

# ✓ MEJOR: Cloud Run env vars (inyectadas en deploy)
# No visible ni en logs ni en backups
```

**En tránsito:**
```python
# Enviamos SOLO headers HTTPS/TLS 1.3
GET https://api.github.com/repos/...
Authorization: Bearer ghp_xxxx
# Token nunca en query params o response body
```

**En logs:**
```python
# ✓ BIEN
logger.info("Conectando GitHub API", extra={"owner": "...", "repo": "..."})

# ❌ MAL
logger.info(f"Token: {GITHUB_API_TOKEN}")  # ← NUNCA
```

**Permisos:**
- Read-only (repo:read, no admin)
- Nunca push, merge, delete
- Rotación cada 90 días
- Alerta si acceso desde IP inusual

---

### 6. ¿Cómo explico un resultado UNKNOWN a un auditor?

**Escenario:**
```
Control: GH-001 (Branch Protection)
Resultado: UNKNOWN
```

**Explicación clara:**
```
"No pudimos evaluar este control porque:
  ├─ Causa 1: Repositorio es privado y token sin acceso (403)
  ├─ Causa 2: GitHub API respondió en timeout (>30s)
  └─ Causa 3: Campo 'branch_protection_enabled' no existe en respuesta

Acción recomendada:
  1. Verificar permisos del token GitHub
  2. Esperar a que GitHub API se recupere
  3. Contactar soporte GitHub si persiste

Para auditoría: revisar audit_logs.error_reason = '403'"
```

El punto clave: **No inventamos datos. Documentamos qué falta.**

---

### 7. ¿Por qué 3 estados en lugar de binario PASS/FAIL?

Lógica de 3 estados es industria estándar:

**Sistemas de 2 estados (PASS/FAIL) son peligrosos:**
```
Control: "Autenticación MFA obligatoria"
Resultado: FAIL (asumimos)

PERO: ¿Qué si el API no respondió?
      ¿Qué si el campo de MFA no existe en la respuesta?
      ¿Qué si el acceso fue denegado?

RIESGO: Reportamos incumplimiento cuando no sabemos.
```

**Sistemas de 3 estados (PASS/FAIL/UNKNOWN) son seguros:**
```
UNKNOWN = "No pudimos determinar" 
        = "Requiere investigación manual"
        = "No reportamos falso negativo"

Admin revisa: ¿Falta permiso? ¿API caída? ¿Repositorio privado?
```

NIST SP 800-53A especifica exactamente esto.

---

## 🐛 TROUBLESHOOTING AVANZADO

### Problema: "SQLAlchemy.exc.OperationalError: could not connect to server"

**Síntomas:**
```
Error: connection refused (postgres not accepting connections)
```

**Diagnóstico:**
```bash
# 1. ¿PostgreSQL está corriendo?
docker-compose ps postgres
# Si no está up → docker-compose up -d postgres

# 2. ¿Está escuchando en puerto 5432?
lsof -i :5432
# Si nada → docker-compose logs postgres

# 3. ¿Timeout de conexión muy corto?
# Ver requirements.txt: DATABASE_POOL_TIMEOUT
```

**Solución:**
```bash
# Opción 1: Reiniciar PostgreSQL
docker-compose restart postgres
sleep 5

# Opción 2: Crear DB fresh
docker-compose down -v  # ⚠️ Borra datos
docker-compose up -d postgres
sleep 10
alembic upgrade head

# Opción 3: Usar PostgreSQL local (no Docker)
# Editar .env: DATABASE_URL=postgresql://user:pass@localhost/db
psql -U securecode_user -d securecode_dev -c "SELECT 1"
```

**Prevención:**
```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U securecode_user"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

### Problema: "pytest: error: unrecognized arguments: --cov"

**Causa:** pytest-cov no instalado

**Solución:**
```bash
pip install pytest-cov

# O
pip install -r requirements-dev.txt
```

---

### Problema: "GitHub 403 Forbidden"

**Síntomas:**
```
GitHubError: 403 Forbidden - Resource not accessible by integration
```

**Causas posibles:**
1. **Token sin permisos suficientes**
   ```bash
   # En GitHub: Settings → Developer Settings → Personal Access Tokens
   # Verificar que tiene: repo (read)
   ```

2. **Repositorio privado sin acceso**
   ```bash
   # Si es repo privado de otra org:
   # Necesita invitación o ser miembro
   ```

3. **Token expirado**
   ```bash
   # Crear nuevo token (Github no notifica vencimiento)
   # Actualizar en .env y en variables de entorno de Cloud Run (--set-env-vars)
   ```

4. **Rate limit:**
   ```bash
   # 60 requests/hour sin autenticación
   # 5000 requests/hour con token
   # Esperar 1 hora o usar nuevo token
   ```

**Solución:**
```python
# En código: capturar y reportar
try:
    response = await client.get(url)
except GitHubError as e:
    if e.status_code == 403:
        logger.error("GitHub 403: revisar permisos token")
        return EvaluationStatus.UNKNOWN  # No evaluar
    raise
```

---

### Problema: "Timeout waiting for connection pool member"

**Síntomas:**
```
asyncpg.exceptions._base.TimeoutError: Timeout waiting for an available connection
```

**Causa:** Connection pool agotado (demasiadas queries concurrentes)

**Soluciones:**

1. **Aumentar tamaño del pool:**
   ```env
   DATABASE_POOL_SIZE=20  # Default 10
   ```

2. **Reducir queries concurrentes:**
   ```python
   # Usar connection pooling nativo
   from sqlalchemy.pool import QueuePool
   
   engine = create_async_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=10,
       max_overflow=20,
       echo=False
   )
   ```

3. **Agregar timeout:**
   ```env
   DATABASE_POOL_TIMEOUT=30  # Segundos
   ```

---

### Problema: "Motor retorna resultado diferente en 2ª ejecución"

**Síntomas:** Reproducibilidad fallida

**Diagnóstico:**
```python
# Ejecutar test_reproducibility_10x
pytest tests/unit/test_engine_evaluator.py::TestRuleEvaluator::test_reproducibility_10x -v
```

**Causas:**
1. **Motor usa random()**
   ```python
   # ❌ MAL
   if random.randint(0, 1):  # Esto hace no-determinista
   ```
   Fix: Usar lógica pura

2. **Motor usa datetime.now()**
   ```python
   # ❌ MAL
   if datetime.now().hour > 12:  # Depende de hora actual
   ```
   Fix: Pasar timestamp como parámetro

3. **Motor tiene state global**
   ```python
   # ❌ MAL
   COUNTER = 0
   def evaluate():
       global COUNTER
       COUNTER += 1  # Cambia entre llamadas
   ```
   Fix: No usar variables globales

**Solución:**
```bash
# Verificar test pasa
pytest tests/unit/test_engine_evaluator.py::test_no_random_in_engine -v
pytest tests/unit/test_engine_evaluator.py::test_no_datetime_in_engine -v
```

---

### Problema: "Ground Truth Accuracy 88%, requiere ≥95%"

**Síntomas:**
```
test_ground_truth_accuracy FAILED: Accuracy 0.88 < 0.95
```

**Diagnóstico:**
```bash
# Ver matriz confusión
pytest tests/ground_truth_validation.py::test_confusion_matrix -v

# Localizar qué casos fallan
pytest tests/ground_truth_validation.py -v -k "fail_001 or fail_002"
```

**Soluciones por tipo de error:**

1. **Falsos Positivos (PASS cuando debería FAIL)**
   ```python
   # Operador equivocado o condición incorrecta
   # Debug: print rule.expression y evidence
   ```

2. **Falsos Negativos (FAIL cuando debería PASS)**
   ```python
   # Lógica AND/OR incorrecta
   # Debug: evaluar cada sub-expresión
   ```

3. **UNKNOWN incorrecto**
   ```python
   # No detectar campos faltantes correctamente
   # Debug: verificar que payload tiene todos campos
   ```

**Plan de acción:**
1. Identificar casos problemáticos (ej: fail_001 a fail_010)
2. Debug manual: print internals de evaluator
3. Arreglar motor
4. Re-ejecutar Ground Truth
5. Target: Accuracy ≥95%, Precision/Recall ≥0.90 por clase

---

### Problema: "Load test P95 latency 12s, requiere ≤3s"

**Síntomas:**
```
Response Time P95: 12s (expected: ≤3s)
Throughput: 10 req/s (expected: ≥50 req/s)
```

**Diagnóstico:**
```bash
# Abrir Locust UI
locust -f tests/load/locustfile.py --host=http://localhost:8000
# Visitar http://localhost:8089
# Ver charts de Response Time

# O en CI/CD
locust ... --csv=results --headless
# Ver results_stats.csv
```

**Causas:**
1. **Queries N+1 en DB**
   ```python
   # ❌ Por cada evaluación, query controls + rules + evidences
   # ✓ Usar eager loading o index
   ```

2. **Connection pool shortage**
   ```env
   DATABASE_POOL_SIZE=10  # Muy bajo para 100 usuarios concurrentes
   # Aumentar a 20-30
   ```

3. **Sin índices en DB**
   ```sql
   CREATE INDEX idx_evaluations_rule_id ON evaluations(rule_id);
   CREATE INDEX idx_evaluations_status ON evaluations(status);
   ```

4. **API sin caching**
   ```python
   # Cachear controles y reglas (no cambian en runtime)
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_control(control_id):
       ...
   ```

**Solución:**
```bash
# Paso 1: Identificar bottleneck
# - DB queries lento? → agregar índices
# - API memory? → reducir cargas en memoria
# - Network? → comprimir responses

# Paso 2: Re-test
make load-test

# Paso 3: Verificar métricas
# P95 ≤ 3s ✓
# P99 ≤ 8s ✓
# Error rate < 1% ✓
```

---

### Problema: "JWT token expirado, pero debería durar 24h"

**Síntomas:**
```
401 Unauthorized: Token expired
# Pero fue creado hace solo 2 horas
```

**Causas:**
1. **Clock skew** (reloj desincronizado)
   ```bash
   # Verificar hora del servidor
   date
   # Si está desincronizada: ntpdate -s time.nist.gov
   ```

2. **Timezone incorrecto**
   ```python
   # ❌ MAL
   expires = datetime.now() + timedelta(hours=24)  # UTC? Local?
   
   # ✓ BIEN
   from datetime import datetime, timezone, timedelta
   expires = datetime.now(timezone.utc) + timedelta(hours=24)
   ```

3. **JWT_ACCESS_TOKEN_EXPIRE_MINUTES incorrecto**
   ```env
   # En .env
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24h * 60
   ```

**Solución:**
```python
# Debug: decodificar token y ver exp
import jwt

token = "eyJhbGc..."
payload = jwt.decode(token, options={"verify_signature": False})
print(payload['exp'])  # Timestamp expiración

# Vs hora actual
from datetime import datetime
now = datetime.utcnow()
print(int(now.timestamp()))

# Si exp < now → Token expirado
```

---

## 📞 CUÁNDO ESCALAR A ARMIN

**Escala si:**
- ❌ Reproducibilidad falla (KPI-01 < 100%)
- ❌ Ground Truth Accuracy < 92% (después 3 intentos fix)
- ❌ Cronograma slip > 5 días
- ❌ Bloqueado en decisión de diseño arquitectónico
- ❌ GitHub API discontinúa endpoint que usamos

**No escales si:**
- ✓ Test falla pero entiendes por qué
- ✓ Desempeño lento pero mejora iterativamente
- ✓ Pregunta general sobre tecnología

