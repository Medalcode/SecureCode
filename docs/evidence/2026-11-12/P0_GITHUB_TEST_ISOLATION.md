# P0 — Aislamiento de pruebas GitHub

- Fecha de ejecución: 2026-11-12, zona horaria America/Santiago.
- Commit de implementación: `e3eacf945191500c433b8dad1b004ec7f083f88e`.
- Entorno: Windows 10, Python 3.14.6, repositorio local `Medalcode/SecureCode`.
- Datos y secretos: no se utilizó token GitHub, DSN, cuenta de cliente ni servicio cloud.

## Problema

El adaptador construía siempre URLs bajo `https://api.github.com`, mientras el
procedimiento de carga declaraba un mock local mediante una variable que el
adaptador no consumía. El proceso de rendimiento dependía además de un
monkeypatch global de `urllib.request.urlopen`.

## Cambio

`UrllibGitHubHttpClient` fija el origen de producción a la API oficial. Las
funciones de adquisición aceptan un cliente inyectable para pruebas. El único
modo de prueba por entorno exige explícitamente
`SECURECODE_GITHUB_TEST_MODE=1` y solo admite
`http://127.0.0.1:8001`; rechaza otros hosts, puertos, esquemas y rutas. El
arranque de rendimiento ya no modifica globalmente el transporte HTTP.

## Evidencia ejecutada

```text
python -m pytest tests/unit/test_github_client_isolation.py \
  tests/unit/test_github_adapter.py tests/unit/test_gh002_adapter.py \
  tests/unit/test_gh002_status_matrix.py tests/unit/test_gh003.py -q \
  -p no:cacheprovider
33 passed in 0.15s

TMP=<repositorio>/.test-tmp
TEMP=<repositorio>/.test-tmp
python -m pytest -q -p no:cacheprovider
179 passed, 13 skipped in 2.68s

python -m ruff check src/securecode/adapters/github.py \
  scripts/run_perf_api.py tests/unit/test_github_client_isolation.py \
  tests/unit/test_github_adapter.py tests/unit/test_gh003.py
All checks passed!
```

Las pruebas del cliente inyectado reemplazan `urlopen` por una función que
falla si se invoca y recorren GH-001, GH-002 y GH-003. También comprueban que
el modo de prueba rechaza destinos distintos del simulador local aprobado.

## Limitaciones y riesgo residual

No se ejecutó Locust ni se midieron recursos en esta fase. La suite de pruebas
omitió 13 casos que requieren PostgreSQL. Windows dejó el directorio temporal
`.test-tmp` con permisos denegados después de la ejecución; está sin versionar
y fuera de cualquier commit.
