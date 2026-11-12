# P1 — Contrato del simulador local de rendimiento

- Fecha de ejecución: 2026-11-12, America/Santiago.
- Commit de implementación: `b684d59`.
- Entorno: Windows 10, Python 3.14.6.
- Red externa: no utilizada. El contrato se prueba con `FastAPI TestClient`.

## Cambio

El simulador local ahora representa los endpoints consumidos por GH-001,
GH-002 y GH-003, incluido `required_signatures`. `MOCK_GITHUB_SCENARIO` permite
reproducir `401`, `403`, `404`, `429` y `500` sin credenciales ni solicitudes a
GitHub. La carga Locust distribuye tareas entre los tres controles y el usuario
de carga recibe una autorización de repositorio local para que la prueba mida
la ruta autorizada de un auditor, no respuestas `403` por preparación incompleta.

## Evidencia ejecutada

```text
python -m pytest tests/unit/test_mock_github.py -q -p no:cacheprovider
7 passed in 0.39s

python -m ruff check scripts/mock_github.py tests/performance/locustfile.py \
  tests/unit/test_mock_github.py
All checks passed!

TMP=<repositorio>/.test-tmp-p1
TEMP=<repositorio>/.test-tmp-p1
python -m pytest -q -p no:cacheprovider
186 passed, 13 skipped in 2.73s
```

## Límites

No se ejecutó una sesión Locust ni se recopilaron métricas de latencia,
CPU, memoria, PostgreSQL o costos en este cambio. Esas mediciones siguen
pendientes y no se derivan de los tests de contrato.
