# Guía de Pruebas de Rendimiento (ES2)

Esta guía detalla los pasos para ejecutar las pruebas de carga reproducibles en el entorno local de SecureCode utilizando Locust.

## Requisitos y Entorno
* **Locust** instalado (`pip install locust`).
* Base de datos local configurada (`securecode_test`).
* Servidor simulado (Mock) para aislar la API de GitHub de solicitudes externas e imitar una latencia predecible de ~200-250ms.

---

## 1. Preparación del Entorno (Ejecutar en terminales separadas)

**Terminal 1: Iniciar Servidor Mock (GitHub)**
```cmd
python scripts\mock_github.py
```
*(El servidor se ejecutará en http://127.0.0.1:8001)*

**Terminal 2: Iniciar API SecureCode (Conectada al Mock y a BD de prueba)**
```cmd
set DATABASE_URL=postgresql+psycopg2://postgres:Muneca1213@localhost:5432/securecode_test
set GITHUB_API_BASE_URL=http://localhost:8001
set PYTHONPATH=src
set JWT_SECRET_KEY=test-secret-key-that-is-at-least-32-bytes-long

python -m uvicorn securecode.api.app:app --host 127.0.0.1 --port 8000
```

---

## 2. Ejecución de Escenarios (Terminal 3)

Antes de correr Locust, asegúrate de setear la misma configuración de la BD para que `on_test_start` pueda inyectar el usuario de pruebas:
```cmd
set DATABASE_URL=postgresql+psycopg2://postgres:Muneca1213@localhost:5432/securecode_test
```

### Escenario A: Smoke Test (Ya Validado)
Comprobación rápida del entorno. 2 usuarios concurrentes, 10 segundos.
```cmd
locust -f tests/performance/locustfile.py --headless -u 2 -r 1 -t 10s --host=http://127.0.0.1:8000 --csv=reports/smoke_test
```

### Escenario B: Carga Nominal
Mide el comportamiento estable del sistema. 50 usuarios concurrentes sostenidos durante 3 minutos.
```cmd
locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 3m --host=http://127.0.0.1:8000 --csv=reports/nominal_load
```

### Escenario C: Concurrencia Progresiva (Ramp-up)
Identifica degradación progresiva de la latencia al inyectar 10 usuarios nuevos por segundo hasta llegar a 200.
```cmd
locust -f tests/performance/locustfile.py --headless -u 200 -r 10 -t 5m --host=http://127.0.0.1:8000 --csv=reports/progressive_load
```

### Escenario D: Estrés Controlado
Busca el punto de quiebre (Timeouts, HTTP 500, DB Exhaustion) empujando a 500 usuarios.
```cmd
locust -f tests/performance/locustfile.py --headless -u 500 -r 20 -t 5m --host=http://127.0.0.1:8000 --csv=reports/stress_load
```

---

## Resultados Esperados / Riesgos (ES2)
* Los archivos `.csv` generados en la carpeta `reports/` contendrán las columnas **p50, p95, req/s (Throughput) y failures**.
* El endpoint de autenticación (`/api/v1/auth/token`) se llama **únicamente 1 vez por VUser** en `on_start()`. Su latencia será intencionalmente alta por **Argon2id** (CPU-bound) pero aislará la medición verdadera del pipeline GH-001 (I/O-bound).
* Si el Escenario D (Estrés) empieza a arrojar `500 Internal Server Error`, revisar que `DATABASE_POOL_SIZE` de SQLAlchemy en la API de FastAPI no esté colapsando por conexiones concurrentes a PostgreSQL.
