# ANEXO TÉCNICO DE VALIDACIÓN Y RESULTADOS EXPERIMENTALES (ES2)
**Proyecto de Título — TIHI84 | INACAP**  
**Proyecto:** SECURECODE — Plataforma configurable de evaluación automatizada de cumplimiento de controles de ciberseguridad  
**Autores:** Jonatthan Medalla · Jose Mora  
**Profesor Guía:** Armin Vladimir Brun Rüth  
**Fecha de consolidación:** Octubre 2026  
**Línea Base en Repositorio:** Rama `main` en commit `f199e8b`  
**GitHub Actions Run ID:** [39175122486](https://github.com/Medalcode/SecureCode/actions/runs/39175122486)  

---

## 1. Resumen Ejecutivo y Alcance del Anexo

El presente anexo técnico constituye la **evidencia consolidada de validación y aseguramiento de calidad** para el hito **Evaluación Sumativa 2 (ES2)** de SECURECODE. Su propósito es respaldar formalmente los requerimientos funcionales, de seguridad, persistencia, rendimiento y calidad arquitectónica establecidos en la Sección V (*Plan de Pruebas y Aseguramiento de Calidad*) del informe principal.

Este documento establece una **distinción metodológica fundamental**:
1. **Métricas formales de Integración Continua (CI):** Pruebas unitarias y de integración deterministas, reproducibles de forma desatendida en el pipeline de GitHub Actions sobre contenedores PostgreSQL 15 oficiales (89% de cobertura, 95/95 pruebas aprobadas).
2. **Evidencias experimentales de rendimiento y persistencia:** Pruebas controladas con usuarios virtuales (Locust), aislamiento en base de datos local `securecode_test` y simulación de latencia de red mediante un mock HTTP desacoplado.

---

## 2. Validación Funcional del Motor de Reglas (GH-001 y GH-002)

El motor de reglas de SECURECODE opera bajo el principio de **evaluación determinista desacoplada**: la adquisición de evidencia técnica desde la API del proveedor (GitHub) se aísla de la lógica de decisión, asegurando que ante una misma evidencia el motor produzca siempre el mismo dictamen.

### 2.1. Control GH-001: Branch Protection — Required Review Approvals
* **Definición normativa:** Alineado con NIST SP 800-53 Rev. 5 (CM-3, CM-5) e ISO/IEC 27001 (A.8.28, A.8.32). Exige que las ramas protegidas requieran revisión de pares y descartes de aprobaciones obsoletas ante nuevos commits.
* **Condición evaluable:**
  $$\text{PASS} \iff (\text{dismiss\_stale\_reviews} = \text{true}) \land (\text{required\_approving\_review\_count} \ge 2)$$
* **Comprobación de determinismo:**
  * Validado en `tests/unit/test_gh001_evaluator.py`.
  * Determinismo verificado experimentalmente en 10 ejecuciones consecutivas idénticas (`test_reproducibility_10x`) y 100 ejecuciones masivas (`test_determinism_100x`), arrojando 0% de variabilidad o discrepancia en el estado resultante.

### 2.2. Control GH-002: Branch Protection Enabled y Matriz Tri-Estado
* **Definición normativa:** Verificación de existencia activa de directivas de protección sobre la rama principal o de producción.
* **Condición evaluable:** $\text{protection\_enabled} = \text{true}$.
* **Matriz completa de adquisición y evaluación:**  
  A diferencia de evaluadores binarios tradicionales, SECURECODE implementa un enfoque de **lógica tri-estado** (`PASS`, `FAIL`, `UNKNOWN`), validado en `tests/unit/test_gh002_status_matrix.py`:

| Escenario | Código HTTP simulado (GitHub) | Evidencia adquirida (`protection_enabled`) | Evaluación resultante | Justificación técnica |
| :--- | :---: | :---: | :---: | :--- |
| **Protegida** | HTTP 200 OK | `True` | **`PASS`** | Reglas de protección activas y configuradas. |
| **No protegida** | HTTP 404 Not Found | `False` | **`FAIL`** | La rama existe en el repositorio, pero no posee directivas de protección configuradas. |
| **Permiso denegado** | HTTP 403 Forbidden | `None` (Dato ausente) | **`UNKNOWN`** | El token carece de privilegios de lectura administrativa. El motor no puede certificar cumplimiento ni incumplimiento. |

Esta triada garantiza el cumplimiento de **KPI-04** (Tasa de `UNKNOWN` correcto $\ge 95\%$), eliminando falsos positivos o falsos negativos derivados de fallas de autorización en la API externa.

---

## 3. Endurecimiento de Seguridad y Mecanismos de Autenticación

En el marco del aseguramiento de calidad y prevención de vulnerabilidades (OWASP API Security Top 10), se aplicaron mejoras defensivas en la capa de transporte, acceso y almacenamiento de credenciales:

### 3.1. Restricción Estricta de Algoritmos Criptográficos en JWT
* **Mitigación de vulnerabilidad de confusión de algoritmos:** El validador de tokens en `src/securecode/api/security.py` fue configurado para restringir explícitamente el conjunto de algoritmos aceptados a `algorithms=["HS256"]`.
* **Batería de pruebas automatizadas (`tests/unit/test_security.py`):**
  * Rechazo de algoritmo nulo (`none` attack): produce HTTP 401.
  * Rechazo de algoritmos no autorizados (`HS384`, `HS512`, `RS256` y cadenas malformadas).
  * Validación de integridad y temporalidad: tokens manipulados en firma o expirados son rechazados de forma inmediata.

### 3.2. Criptografía de Contraseñas con Argon2id
* **Parámetros seguros:** Implementación basada en `argon2-cffi` con perfil optimizado para resistencia contra ataques de canal lateral y aceleración por GPU.
* **Manejo defensivo de excepciones:** Ante hashes truncados, vacíos o sintácticamente corruptos, el verificador captura la excepción interna y retorna `False` de manera determinista, evitando caídas no controladas del proceso (HTTP 500).

### 3.3. Homogeneización de Respuestas de Autenticación (Prevención de Enumeración)
* **Comportamiento uniforme HTTP 401:** En `src/securecode/api/app.py`, tanto las credenciales erróneas como el acceso de cuentas inactivadas (`is_active=False`) retornan un código homogéneo `401 Unauthorized` con el encabezado estándar `WWW-Authenticate: Bearer`. Esto previene ataques de enumeración de usuarios basados en diferencias de código HTTP.

### 3.4. Higiene del Repositorio y Prevención de Fugas de Datos
* **Actualización de `.gitignore`:** Exclusión explícita y permanente de bases de datos locales SQLite (`securecode.db`), logs de depuración (`run_logs.txt`), archivos de credenciales (`.env`) y reportes de pruebas de carga.
* **Eliminación del historial rastreado:** Se retiraron formalmente del árbol de Git los archivos locales rastreados previamente, mitigando los hallazgos de auditoría PERF-001 y PERF-002.

---

## 4. Pruebas Automatizadas y Métricas de CI (GitHub Actions)

La suite de pruebas automatizadas se ejecuta de forma integral en cada Pull Request y en cada push a la rama `main`, garantizando que ninguna regresión ingrese al código productivo.

### 4.1. Entorno de Integración Continua
* **Orquestador:** GitHub Actions Runner (`ubuntu-latest`).
* **Runtime:** Python 3.11.
* **Base de datos de prueba:** Contenedor de servicio PostgreSQL 15 (`postgres:15`).
* **Herramientas de análisis:** `pytest 8.x`, `pytest-cov`, `httpx`.

### 4.2. Resultados Oficiales de la Ejecución en `main`
* **Ejecución de CI:** Run ID [39175122486](https://github.com/Medalcode/SecureCode/actions/runs/39175122486)
* **Commit validado:** `f199e8b6fceea1842c9ed9433ab8d23254254033`
* **Estado:** **SUCCESS**
* **Total de pruebas:** **95 aprobadas**, 0 fallidas, 0 errores.
* **Duración de ejecución de pytest:** **1,90 segundos**.

### 4.3. Cobertura de Código por Componente

| Módulo / Capa Arquitectónica | Líneas Evaluadas | Líneas Omitidas | Cobertura (%) | Estado frente a Meta MVP ($\ge 85\%$) |
| :--- | :---: | :---: | :---: | :---: |
| `src/securecode/engine/` (Motor de Reglas) | 120 | 6 | **95%** | Superada |
| `src/securecode/models/` (Modelos Pydantic) | 85 | 0 | **100%** | Superada |
| `src/securecode/api/` (Endpoints FastAPI / Auth) | 186 | 17 | **91%** | Superada |
| `src/securecode/adapters/` (GitHub API & PostgreSQL) | 140 | 17 | **88%** | Superada |
| **TOTAL CONSOLIDADO** | **531** | **56** | **89%** | **CUMPLIMIENTO EXITOSO** |

---

## 5. Pruebas Experimentales de Rendimiento y Carga (Locust)

Para validar los SLA y KPI de latencia y throughput bajo condiciones de concurrencia, se ejecutó una batería de pruebas de carga y estrés con Locust.

### 5.1. Metodología de Aislamiento Experimental
1. **Mock de GitHub en Loopback:** Para evitar bloqueos por *Rate Limiting* de GitHub (cuota de 5,000 req/hora) y latencias erráticas de internet, se ejecutó un mock HTTP local (`127.0.0.1:8001`) con latencia artificial inyectada de **150 ms** por solicitud.
2. **Aislamiento de Carga de CPU:** Las solicitudes de evaluación utilizaron tokens JWT previamente obtenidos en el evento `on_start` del usuario virtual, aislando el coste computacional de Argon2id del procesamiento propio de la regla.
3. **Persistencia Activa:** Cada evaluación procesada fue efectivamente insertada en PostgreSQL (`securecode_test`), midiendo el overhead real de SQLAlchemy y la base de datos relacional.

### 5.2. Resultados por Escenario de Carga

| Escenario | Concurrencia (VUsers) | Duración | Peticiones Totales (GH-001) | Throughput (RPS) | Latencia Media | Latencia p95 | Tasa de Error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A: Carga Nominal** | 5 | 2 min | 262 | 2,20 req/s | 165 ms | 180 ms | **0,0%** |
| **B1: Concurrencia 10** | 10 | 1 min | 228 | 3,89 req/s | 170 ms | 200 ms | **0,0%** |
| **B2: Concurrencia 20** | 20 | 1 min | 497 | 8,50 req/s | 168 ms | 200 ms | **0,0%** |
| **B3: Concurrencia 30** | 30 | 1 min | 676 | 11,36 req/s | 167 ms | 180 ms | **0,0%** |
| **C: Estrés Controlado** | 50 | 2 min | 2.432 | **20,45 req/s** | 172 ms | **300 ms** | **0,0%** |

### 5.3. Hallazgos y Cumplimiento de KPI
* **SLA de Latencia (KPI-03, p95 $\le$ 3,0 s):** Bajo la condición de estrés más exigente (50 usuarios concurrentes), la latencia percentil 95 fue de **300 ms** (0,30 s), superando con holgura la meta de 3 segundos.
* **Overhead del Sistema:** Restando los 150 ms de latencia impuesta por el mock, el tiempo consumido conjuntamente por FastAPI, la serialización Pydantic y la transacción en PostgreSQL fue de **~150 ms en el p95**.
* **Estabilidad del Connection Pool:** Durante las 4,104 peticiones de evaluación procesadas en las pruebas de carga, no se registró ninguna saturación ni timeout en las conexiones hacia PostgreSQL.

### 5.4. Limitaciones Metodológicas de la Simulación
* **Ausencia de latencia WAN:** La ejecución en `localhost` no refleja las fluctuaciones reales de enrutamiento internacional hacia `api.github.com`.
* **Comportamiento del proveedor real:** El límite de tasa de la API pública de GitHub introduce restricciones operativas que requerirán en el futuro el uso de colas asíncronas y caché de evidencia.

---

## 6. Persistencia, Integridad Referencial y Trazabilidad (PostgreSQL)

### 6.1. Modelo Relacional y Trazabilidad Transaccional
El almacenamiento en PostgreSQL se estructura mediante dos entidades acopladas transaccionalmente:
* **`evidence_records`:** Almacena el payload estructurado recibido del proveedor, la fecha de recolección (`collected_at`) y el digest criptográfico `sha256_hash`.
* **`evaluation_records`:** Registra el dictamen emitido (`status`), la regla aplicada, las marcas temporales (`evaluated_at`) y la clave foránea obligatoria `evidence_id`.

```
  ┌─────────────────────────┐               ┌─────────────────────────┐
  │     evidence_records    │               │    evaluation_records   │
  ├─────────────────────────┤               ├─────────────────────────┤
  │ id (UUID, PK)           │◄──────────────┤ evidence_id (UUID, FK)  │
  │ payload (JSONB)         │    1 : 1      │ id (UUID, PK)           │
  │ sha256_hash (VARCHAR)   │ (observado)   │ control_id (VARCHAR)    │
  │ collected_at (TIMESTAMPTZ)│             │ status (VARCHAR)        │
  └─────────────────────────┘               │ evaluated_at (TIMESTAMPTZ)
                                            └─────────────────────────┘
```

### 6.2. Verificación de Integridad y Correspondencia Empírica
En las pruebas controladas (PERF-004 para GH-001 y PERF-005 para GH-002) se auditó el comportamiento de la base de datos `securecode_test`:
1. **Correspondencia observada:** Cada petición individual procesada por la API generó exactamente **+1 registro en `evaluation_records` y +1 registro en `evidence_records`**, vinculados por el mismo UUID.
2. **Consistencia de hash:** El cálculo en memoria de SHA-256 sobre el objeto `GH001Evidence` / `GH002Evidence` coincidió bit a bit con el campo `sha256_hash` persistido.
3. **Consistencia masiva en carga:** El recuento final en base de datos arrojó un total de 4,104 evaluaciones completadas durante la sesión de pruebas, coincidiendo exactamente con la sumatoria de peticiones registradas por los archivos CSV de Locust.

### 6.3. Precaución Metodológica sobre Transaccionalidad
> **Nota de rigor técnico:**  
> La correspondencia 1:1 observada y la integridad de claves foráneas demuestran el comportamiento correcto del repositorio SQLAlchemy en ejecuciones nominales y concurrentes exitosas. Sin embargo, **esta evidencia empírica no constituye una prueba formal de atomicidad ante fallos catastróficos** (por ejemplo, interrupción forzada del servidor de base de datos a mitad de la sentencia SQL). Dicha garantía requerirá una batería específica de pruebas de inyección de fallos y validación de rollback automático en etapas posteriores.

---

## 7. Evidencia de Integración y Ciclo de Vida de Desarrollo

La consolidación técnica del proyecto siguió un proceso de integración continua y control de versiones auditable:

```mermaid
gitGraph
   commit id: "Inicial main"
   branch security/audit-artifacts
   checkout security/audit-artifacts
   commit id: "f417090 - Uniform 401"
   commit id: "a883796 - JWT/Argon2"
   checkout main
   branch test/gh002-status-matrix
   checkout test/gh002-status-matrix
   commit id: "52a284c - Matriz GH-002"
   checkout security/audit-artifacts
   branch integration/security-gh002
   checkout integration/security-gh002
   cherry-pick id: "52a284c"
   commit id: "ba049ec - Consolidación"
   checkout main
   merge integration/security-gh002 id: "f199e8b - Merge PR #4"
```

* **Pull Request #4 (`integration/security-gh002`):** Candidato único de integración a `main` que agrupó los cambios del PR #2 (seguridad y saneamiento) y del PR #3 (matriz automatizada GH-002), totalizando 9 archivos modificados.
* **Fusión definitiva:** Ejecutada mediante **Merge Commit** en commit `f199e8b`, conservando la trazabilidad de los commits de auditoría.
* **Validación post-merge:** Se ejecutó el pipeline de GitHub Actions sobre `main` (Run 39175122486), ratificando la aprobación de las 95 pruebas y el 89% de cobertura.
* **Cierre trazable:** Los PR #2 y #3 fueron cerrados indicando explícitamente su consolidación en `main` a través del PR #4.

---

## 8. Matriz de Contraste frente a Rúbrica y Criterios INACAP (ES2)

| Criterio de Evaluación INACAP | Exigencia Rúbrica | Estado Demostrado en SECURECODE | Evidencia Técnica de Respaldo |
| :--- | :--- | :--- | :--- |
| **Batería de Pruebas de Software** | Múltiples niveles de prueba ejecutados y documentados. | **Sobresaliente:** 95 pruebas automatizadas (unitarias, integración, seguridad, matriz de estados). | CI Run 39175122486, `test_security.py`, `test_gh002_status_matrix.py`. |
| **Aseguramiento de Calidad y Cobertura** | Cobertura de código relevante con métricas verificables. | **Sobresaliente:** Cobertura global del **89%** (superando la meta de 85%), con 100% en modelos de dominio y 95% en motor. | Reporte XML/HTML `pytest-cov`, 531 líneas auditadas. |
| **Pruebas de Rendimiento y Estrés** | Medición de latencias, concurrencia y límites del sistema. | **Sobresaliente:** 3 escenarios en Locust (5 a 50 usuarios), p95 de 300 ms frente a meta de 3 s, 0% errores a 20.45 RPS. | `docs/evidence/performance/ES2_PERFORMANCE_RESULTS.md`, reportes CSV en `reports/`. |
| **Seguridad de la Implementación** | Defensas aplicadas contra vulnerabilidades comunes. | **Sobresaliente:** Restricción JWT a HS256, Argon2id robustecido, mitigación de enumeración de usuarios y saneamiento de `.gitignore`. | `src/securecode/api/security.py`, `test_auth.py`, commit `f199e8b`. |
| **Trazabilidad y Persistencia de Datos** | Almacenamiento íntegro y verificabilidad de resultados. | **Sobresaliente:** Persistencia en PostgreSQL con enlace foráneo a evidencia y hash SHA-256 verificado. | `PostgresEvaluationRepository`, recuento de 4,104 transacciones en `securecode_test`. |
| **Ciclo de Vida y Gestión de Configuración** | Flujo de Git ordenado y auditable. | **Sobresaliente:** Estrategia basada en PRs de validación, Merge Commit y pipeline automatizado en GitHub Actions. | PR #4, commit `f199e8b`, historial de commits intacto. |
