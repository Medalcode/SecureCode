# P3 — Enterprise Trial: API y límites aplicados

## Alcance implementado

Sobre la fundación y migración `aa7c1e9d4f30`, esta entrega expone un flujo API
autenticado para un Enterprise Trial técnico y no facturable:

- `GET /api/v1/enterprise-trial`: consulta únicamente el estado del usuario
  autenticado, sus cuotas y los repositorios autorizados.
- `POST /api/v1/enterprise-trial`: activa una sola vez el trial de 14 días,
  previa confirmación explícita y con nombre de organización.
- `POST /api/v1/enterprise-trial/repositories`: permite al propietario agregar
  hasta tres repositorios al scope del trial.
- Las evaluaciones GH-001, GH-002 y GH-003 de un usuario con trial activo
  requieren `Idempotency-Key`, usan únicamente repositorios del scope del
  trial y reservan la cuota antes de consultar GitHub. La reserva queda
  completada sólo después de persistir la evaluación; si la evaluación falla,
  se libera.

La cuota predeterminada permanece en 14 días, 3 repositorios y 100
evaluaciones. No se añadieron pagos, precios, checkout, renovaciones ni
reconocimiento de ingresos. La respuesta declara `trial_non_billable`.

## Controles verificables

- Un usuario no autenticado recibe `401`.
- La activación sin confirmación recibe `422`.
- Una cuenta no puede activar un segundo trial, incluso tras vencimiento.
- El cuarto repositorio recibe `409`.
- Una evaluación de trial sin `Idempotency-Key` recibe `400`.
- Un reintento con la misma clave recibe `409`, sin volver a gastar cuota.
- La cuenta de prueba confirmó una evaluación completada y 99 unidades
  restantes del límite de 100.

## Evidencia de prueba

Entorno: Windows local, Python 3.14.6 y SQLite en memoria para contratos HTTP.
No se emplearon GitHub real, Cloud Run, Supabase, Neon, facturación ni datos
comerciales.

```text
python -m pytest tests/api/test_enterprise_trial_http.py \
  tests/unit/test_enterprise_trial.py tests/api/test_app.py \
  tests/api/test_gh002_app.py tests/api/test_admin_http.py -q
24 passed in 2.20s
```

Como verificación de regresión se ejecutó además la suite completa con un
directorio temporal dentro del repositorio:

```text
python -m pytest -q -p no:cacheprovider --basetemp=.test-tmp-enterprise-full
203 passed, 13 skipped in 3.74s
```

## Interfaz implementada

La página autenticada **Plan & SLA** consume los endpoints anteriores y
muestra el estado disponible, activo o vencido. Permite ingresar el nombre de
organización, exige confirmación antes de activar, muestra días y cuotas
restantes, y permite añadir repositorios hasta el límite. También comunica
explícitamente que el trial es no facturable y que no modifica la suscripción
comercial.

La interfaz no intenta generar cobros ni inventa precios. Cuando el trial está
activo, el evaluador genera y envía una `Idempotency-Key` nueva por cada
ejecución, de modo que el límite se aplique sin exponer ese detalle operativo
al usuario final.

Verificación adicional de interfaz:

```text
node --check src/securecode/static/js/app.js
python -m pytest tests/api/test_frontend_routes.py \
  tests/api/test_enterprise_trial_http.py tests/api/test_admin_http.py -q
11 passed in 1.46s
```
