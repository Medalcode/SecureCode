# Guía de Pruebas de Rendimiento (ES2)

Esta guía detalla los pasos para ejecutar las pruebas de carga reproducibles en el entorno local de SecureCode utilizando Locust.

## Requisitos y Entorno
* **Locust** instalado (`pip install locust`).
* Base de datos local configurada (`securecode_test`).
* Servidor simulado (Mock) para aislar la API de GitHub de solicitudes externas.

No ejecutes esta guía contra Supabase, Neon, Cloud Run, una base comercial ni
una credencial GitHub real.

---

## 1. Preparación del Entorno (Ejecutar en terminales separadas)

**Terminal 1: Iniciar Servidor Mock (GitHub)**
```cmd
python scripts\mock_github.py
```
*(El servidor se ejecutará en http://127.0.0.1:8001)*

**Terminal 2: Iniciar API SecureCode (Conectada al Mock y a BD de prueba)**
```cmd
REM Configurar la URL de conexión usando variables de entorno seguras (no incluir contraseñas en código)
set DATABASE_URL=postgresql+psycopg2://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5432/securecode_test
set SECURECODE_GITHUB_TEST_MODE=1
set SECURECODE_GITHUB_TEST_BASE_URL=http://127.0.0.1:8001
set PYTHONPATH=src
set JWT_SECRET_KEY=test-secret-key-that-is-at-least-32-bytes-long

python scripts\run_perf_api.py
```

---

## 2. Ejecución de Escenarios (Terminal 3)

Antes de correr Locust, asegúrate de setear la misma configuración de la BD para que `on_test_start` pueda inyectar el usuario de pruebas:
```cmd
set DATABASE_URL=postgresql+psycopg2://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5432/securecode_test
```

### Escenarios de carga configurados

`tests/performance/locustfile.py` distribuye solicitudes entre GH-001, GH-002,
GH-003 y `/health`. Conserva los CSV junto con fecha, SHA y entorno; estos
comandos no prueban por sí solos un SLA actual.

1. **Smoke Test previo**: Comprobación rápida del entorno (2 VUsers, 10 segundos).
   ```cmd
   locust -f tests/performance/locustfile.py --headless -u 2 -r 1 -t 10s --host=http://127.0.0.1:8000 --csv=reports/smoke_test
   ```
2. **Escenario A — Carga Nominal**: 5 usuarios concurrentes, 2 minutos, ramp-up 1/s.
   ```cmd
   locust -f tests/performance/locustfile.py --headless -u 5 -r 1 -t 2m --host=http://127.0.0.1:8000 --csv=reports/nominal_load
   ```
3. **Escenario B — Concurrencia Progresiva**:
   * Nivel 1: 10 usuarios concurrentes, 1 minuto, ramp-up 2/s (`--csv=reports/progressive_10`).
   * Nivel 2: 20 usuarios concurrentes, 1 minuto, ramp-up 2/s (`--csv=reports/progressive_20`).
   * Nivel 3: 30 usuarios concurrentes, 1 minuto, ramp-up 2/s (`--csv=reports/progressive_30`).
4. **Escenario C — Estrés Controlado**: 50 usuarios concurrentes, 2 minutos, ramp-up 5/s.
   ```cmd
   locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 2m --host=http://127.0.0.1:8000 --csv=reports/stress_load
   ```

*(Nota: Para ejecutar la suite completa de forma desatendida, se utiliza el script `powershell -File run_perf_tests.ps1`).*

## 3. Medición de consumo por control y perfil

El recolector local genera evidencia por control y perfil sin calcular costos
ni cambiar supuestos financieros. Con API, mock y `securecode_test` local ya
iniciados, define credenciales de un usuario de carga local:

```cmd
set SECURECODE_PERF_USERNAME=perf_user
set SECURECODE_PERF_PASSWORD=<solo-clave-local>
python scripts\measure_local_performance.py --output-dir reports\YYYY-MM-DD-local
```

Por defecto se ejecutan 100 evaluaciones por combinación de los controles
GH-001, GH-002 y GH-003 con perfiles de simulador `small`, `medium` y `large`:
900 observaciones. El mock asocia esos perfiles a repositorios locales
`securecode-small`, `securecode-medium` y `securecode-large`, con latencias
simuladas de 10, 50 y 100 ms; no representan repositorios GitHub reales. El
resultado incluye `observations.csv` y `summary.json` con
latencia, bytes de respuesta, estado HTTP, P95, tamaño de tablas PostgreSQL,
conteo del simulador y CPU/RSS opcional del proceso API:

```cmd
python scripts\measure_local_performance.py ^
  --api-pid <PID_DEL_PROCESO_API> ^
  --output-dir reports\YYYY-MM-DD-local
```

La herramienta rechaza URLs distintas de `127.0.0.1` y una `DATABASE_URL` que
no apunte a `localhost:5432/securecode_test`. Si una solicitud falla, conserva
el CSV para análisis y retorna código distinto de cero.

## 4. Estado de evidencia

Los benchmarks históricos en `docs/evidence/performance/` no son mediciones
actuales del flujo de tres controles. Al actualizar ES2, diferencia resultados
históricos, simulados y mediciones nuevas verificables.

---

## Resultados Esperados / Riesgos (ES2)
* Los archivos `.csv` generados en la carpeta `reports/` contendrán las columnas **p50, p95, p98, req/s (Throughput) y failures**.
* El endpoint de autenticación (`/api/v1/auth/token`) se llama **únicamente 1 vez por VUser** en `on_start()`. Su latencia será intencionalmente mayor por **Argon2id** (CPU-bound) pero aislará la medición verdadera del pipeline GH-001 (I/O-bound).
* Si el Escenario de Estrés empieza a arrojar `500 Internal Server Error`, revisar que el connection pool de SQLAlchemy en la API de FastAPI no esté colapsando por conexiones concurrentes a PostgreSQL.
