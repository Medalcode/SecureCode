# P2 — Protocolo de medición local de consumo

- Fecha de implementación: 2026-11-12, America/Santiago.
- Commit de implementación: `6f1fb1b`.
- Entorno de prueba de automatización: Windows 10, Python 3.14.6.

## Alcance implementado

`scripts/measure_local_performance.py` exige API y mock locales fijos,
`securecode_test` local y credenciales de carga entregadas solo por variables
de entorno. No registra esas credenciales, un token ni una URL de base de
datos. Emite `observations.csv` y `summary.json` con tiempo por solicitud,
bytes de respuesta, estado HTTP, P95, CPU/RSS del proceso opcional, tamaños
PostgreSQL antes/después y diferencia de llamadas al simulador.

Por defecto recorre los tres controles, tres perfiles de simulador y 100
evaluaciones por combinación: 900 observaciones. Esta es una capacidad del
protocolo, no una ejecución de 900 evaluaciones realizada en esta evidencia.

## Evidencia ejecutada

```text
python -m pytest tests/unit/test_measure_local_performance.py \
  tests/unit/test_mock_github.py -q -p no:cacheprovider
12 passed in 0.50s

python -m ruff check scripts/measure_local_performance.py scripts/mock_github.py \
  tests/unit/test_measure_local_performance.py tests/unit/test_mock_github.py \
  tests/performance/locustfile.py
All checks passed!

TMP=<repositorio>/.test-tmp-p3
TEMP=<repositorio>/.test-tmp-p3
python -m pytest -q -p no:cacheprovider
191 passed, 13 skipped in 2.77s
```

## Pendiente

No existe todavía un CSV de medición de 900 evaluaciones ni datos de factura
cloud. Por tanto no hay costo observado ni facturado que integrar al modelo
financiero; el script no calcula CLP ni altera supuestos comerciales.
