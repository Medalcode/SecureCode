# Guía de Pruebas de Rendimiento (ES2)

Esta guía detalla los pasos para ejecutar las pruebas de carga reproducibles en el entorno local de SecureCode utilizando Locust.

## Requisitos y Entorno
* **Locust** instalado (`pip install locust`).
* Base de datos local configurada (`securecode_test`).
* Servidor simulado (Mock) para aislar la API de GitHub de solicitudes externas e imitar una latencia predecible de ~150ms.

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
set GITHUB_API_BASE_URL=http://localhost:8001
set PYTHONPATH=src
set JWT_SECRET_KEY=test-secret-key-that-is-at-least-32-bytes-long

python -m uvicorn securecode.api.app:app --host 127.0.0.1 --port 8000
```

---

## 2. Ejecución de Escenarios (Terminal 3)

Antes de correr Locust, asegúrate de setear la misma configuración de la BD para que `on_test_start` pueda inyectar el usuario de pruebas:
```cmd
set DATABASE_URL=postgresql+psycopg2://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5432/securecode_test
```

### Escenarios Empíricos Ejecutados para ES2 (Automatizados en `run_perf_tests.ps1`)

Los siguientes escenarios constituyen la batería formal ejecutada y documentada en los reportes de rendimiento de ES2:

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

### Escenarios Teóricos Propuestos (Para Escalabilidad Cloud Futura)
Como parte del roadmap de capacidad en entornos distribuidos (Cloud Run + Cloud SQL), se contemplan escenarios de mayor envergadura no reproducibles en un único host local:
* **Escalabilidad Media:** 200 usuarios concurrentes (ramp-up 10/s, 5 min).
* **Estrés Límite de Infraestructura:** 500 usuarios concurrentes (ramp-up 20/s, 5 min).

---

## Resultados Esperados / Riesgos (ES2)
* Los archivos `.csv` generados en la carpeta `reports/` contendrán las columnas **p50, p95, p98, req/s (Throughput) y failures**.
* El endpoint de autenticación (`/api/v1/auth/token`) se llama **únicamente 1 vez por VUser** en `on_start()`. Su latencia será intencionalmente mayor por **Argon2id** (CPU-bound) pero aislará la medición verdadera del pipeline GH-001 (I/O-bound).
* Si el Escenario de Estrés empieza a arrojar `500 Internal Server Error`, revisar que el connection pool de SQLAlchemy en la API de FastAPI no esté colapsando por conexiones concurrentes a PostgreSQL.
