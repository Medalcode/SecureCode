# P3 — Fundación técnica Enterprise Trial

- Fecha de ejecución: 2026-11-12, America/Santiago.
- Commits de implementación: `545a9c2` y `c944452` (cadena Alembic corregida).
- Entorno: Windows 10, Python 3.14.6, SQLite en memoria para las pruebas de
  política. No se utilizó PostgreSQL comercial, Supabase, GitHub ni credenciales.

## Implementado

La migración `aa7c1e9d4f30` añade organizaciones, membresías, trials,
repositorios autorizados y reservas de uso con clave de idempotencia. La capa
de aplicación implementa una política configurable con valor base de 14 días,
3 repositorios y 100 evaluaciones. Las reservas se bloquean a nivel de fila en
PostgreSQL y se liberan si la evaluación falla antes de completarse.

No se añadió checkout, facturación, precio, estimación de conversión ni ingreso
reconocido. Tampoco se expuso todavía la funcionalidad como un flujo de UI/API
para clientes: esta entrega prepara y prueba la capa de dominio y su migración.

## Evidencia ejecutada

```text
python -m pytest tests/unit/test_enterprise_trial.py \
  tests/unit/test_measure_local_performance.py tests/unit/test_mock_github.py \
  -q -p no:cacheprovider
17 passed in 1.50s

python -m ruff check src/securecode/application/enterprise_trial.py \
  src/securecode/adapters/postgres/models.py \
  alembic/versions/aa7c1e9d4f30_enterprise_trials.py \
  tests/unit/test_enterprise_trial.py
All checks passed!

TMP=<repositorio>/.test-tmp-p5
TEMP=<repositorio>/.test-tmp-p5
python -m pytest -q -p no:cacheprovider
196 passed, 13 skipped in 3.51s
```

Las pruebas demuestran 100 reservas permitidas y la 101 bloqueada, tres
repositorios permitidos y el cuarto bloqueado, expiración, aislamiento por
membresía y reintentos idempotentes. La concurrencia real en PostgreSQL y la
migración sobre Supabase siguen pendientes de ejecución controlada.

Verificación de migraciones posterior a la corrección:

```text
alembic heads
aa7c1e9d4f30 (head)
```
