# SECURECODE — Informe Experimental de Rendimiento (ES2)

Este documento contiene la evidencia experimental obtenida tras ejecutar la suite de rendimiento aislada con Locust contra el entorno local de pruebas (`securecode_test`), según las directrices establecidas para el hito ES2.

## 1. Metodología Experimental y Entorno

- **Aislamiento de Dependencias**: Para asegurar una medición de I/O puro y evitar el *Rate Limiting* de GitHub, se inyectó un parche en tiempo de ejecución (`run_perf_api.py`) que intercepta `urllib.request` y redirige el tráfico a un **Mock HTTP local**. 
- **Latencia Artificial (Mock)**: El servidor Mock inyectó deliberadamente latencias de **150ms** (fetch rules) simulando el comportamiento típico de la API productiva al evaluar la protección de ramas.
- **Aislamiento de CPU**: Para evitar que el alto coste computacional de **Argon2id** contaminara el rendimiento general de las evaluaciones, los usuarios virtuales (Locust `HttpUser`) realizaron el inicio de sesión (`/api/v1/auth/token`) una única vez en su ciclo de vida (`on_start`).
- **Base de Datos**: Se utilizó PostgreSQL (v17) mediante el schema `securecode_test`. Las conexiones fueron manejadas por el connection pool de SQLAlchemy en FastAPI.

### Componentes de software:
- **Python**: 3.14.6
- **Locust**: 2.46.7
- **Base de Datos**: PostgreSQL 17.0 (Local/Dockerizado)
- **Framework Web**: FastAPI (Uvicorn HTTP/1.1)

---

## 2. Resultados por Escenario

Los escenarios de carga probaron los límites del sistema aumentando gradualmente la cantidad de usuarios virtuales (VUsers). Las métricas extraídas corresponden a los registros CSV generados por Locust.

### 2.1. Escenario A: Carga Nominal (5 VUsers, 2 minutos, Ramp-up 1/seg)
**Objetivo:** Establecer una línea de base sin estrés.
* **POST `/api/v1/evaluations/gh-001`**:
  * Peticiones totales: 262
  * Latencia Media: 165ms
  * Latencia p95: 180ms
  * Throughput (RPS): 2.20 req/s
* **Errores Totales**: 0 (0%)

### 2.2. Escenario B: Concurrencia Progresiva (10, 20 y 30 VUsers, 1 min por nivel)
**Objetivo:** Observar la degradación lineal al aumentar la concurrencia.
* **Nivel 10 VUsers**: GH-001 p95 = 200ms | Throughput = 3.89 RPS | Errores = 0
* **Nivel 20 VUsers**: GH-001 p95 = 200ms | Throughput = 8.50 RPS | Errores = 0
* **Nivel 30 VUsers**: GH-001 p95 = 180ms | Throughput = 11.36 RPS | Errores = 0

*Nota: La latencia se mantuvo estable debido a la naturaleza asíncrona de FastAPI, que delegó eficientemente los tiempos de espera del Mock.*

### 2.3. Escenario C: Estrés Controlado (50 VUsers, 2 minutos, Ramp-up 5/seg)
**Objetivo:** Encontrar degradación de servicios o cuellos de botella.
* **POST `/api/v1/evaluations/gh-001`**:
  * Peticiones totales: 2432
  * Latencia Media: 172ms
  * Latencia p95: **200ms** (p98: 300ms)
  * Throughput (RPS): **20.45 req/s**
* **GET `/health` (Baseline)**:
  * Latencia Media: 2ms
  * Latencia p95: 4ms
* **POST `/api/v1/auth/token`**:
  * Latencia Media: 154ms
  * Latencia p95: **200ms** (p98: 240ms)
* **Errores Totales**: 0 (0%)

---

## 3. Análisis de Resultados (Comparación y Degradación)

1. **Rendimiento de Evaluación y Persistencia (GH-001)**: El sistema logró procesar **~20.4 evaluaciones por segundo** bajo estrés, completando 2.432 evaluaciones en este escenario (y 4.095 transacciones a lo largo de los cinco escenarios principales) con **0% de tasa de error**. La distribución de tiempos exhibió una mediana de 160ms y un p95 de **200ms** (alcanzando 300ms en el percentil 98). Frente al retardo base de 150ms inyectado por el mock en el endpoint de branch protection, el tiempo adicional aportado por FastAPI, la serialización de modelos Pydantic y la persistencia relacional en PostgreSQL se mantuvo estrecho y predecible bajo concurrencia.
2. **Impacto de la Autenticación (Argon2id)**: Durante el *ramp-up* del escenario de estrés, se solicitaron 5 hashes de contraseña por segundo. Esto incrementó la latencia p95 de autenticación a **200ms** (con p98 de 240ms), reflejando la demanda intensiva de CPU de la función criptográfica. No obstante, al haberse aislado la obtención del token al inicio de sesión (`on_start`), el procesamiento de las evaluaciones GH-001 no se vio degradado.
3. **Estabilidad de PostgreSQL**: SQLAlchemy manejó eficientemente las transacciones. No se observaron excepciones de *Timeout* ni agotamiento de conexiones (Connection Pool Exhaustion) durante los picos de 20 RPS.

---

## 4. Limitaciones del Experimento

A pesar de ser estadísticamente significativos, los datos poseen las siguientes limitaciones que deben considerarse al establecer un SLA real:
* **Latencia de Red Externa Simulada**: Los resultados asumen que GitHub responderá siempre en ~150ms sin fallos ni interrupciones. En producción, la latencia real de la red, los bloqueos geográficos y el Rate Limit de GitHub (5000 req/hr) degradarán considerablemente el rendimiento máximo alcanzable.
* **Coste de Red Interna (Localhost)**: Al correr DB, App, Locust y Mock en la misma máquina local, no existe latencia de red real entre los microservicios, lo cual arroja latencias (como los 2ms de `/health`) que no serán reproducibles en un despliegue distribuido de Cloud Run.

---

## 5. Conclusión y Evidencia

El experimento demuestra empíricamente que la arquitectura orquestada (FastAPI + Pydantic + PostgreSQL + JWT) es **robusta y libre de cuellos de botella severos** en la capa de negocio bajo condiciones controladas de prueba. 

**Resumen de Indicadores Clave:**
* **Throughput Demostrado (GH-001)**: ~20.4 RPS.
* **Tasa de Errores**: 0.0% bajo cargas de 50 usuarios concurrentes.
* **Evaluaciones Persistidas Confirmadas**: 
  * **4.095** evaluaciones GH-001 registradas en los 5 escenarios formales (262 nominal + 228 prog10 + 497 prog20 + 676 prog30 + 2.432 estrés).
  * **4.104** evaluaciones generadas por Locust al incluir el Smoke Test previo (+9 peticiones).
  * Consistente con el recuento acumulado en la base de datos `securecode_test`.

Los reportes detallados y CSV originales generados por la herramienta se encuentran versionados en el directorio `reports/` del repositorio.
