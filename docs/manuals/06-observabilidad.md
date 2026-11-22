# Manual de observabilidad — SecureCode (Fase 12)

Este manual describe la telemetría emitida por el código fuente local de SecureCode. La instrumentación es de biblioteca estándar de Python y no instala exportadores, agentes ni servicios externos. Las alertas y la retención descritas son **propuestas operacionales**: no se han creado recursos, canales, reglas ni workspaces en Google Cloud.

## 1. Fuentes y arquitectura

| Fuente | Destino | Estado |
|---|---|---|
| Logs JSON de aplicación | `stdout`; Cloud Run los recoge como logs estructurados | Implementado |
| Logs de Uvicorn | `stdout` con el mismo formateador JSON | Implementado |
| Métricas HTTP y de evaluación | Contadores/histogramas agregados por proceso, disponibles en `GET /internal/observability/metrics` para `platform_admin` | Implementado, ámbito por instancia |
| Métricas globales multi-instancia | Log-based metrics de Google Cloud Monitoring construidas desde los eventos JSON | Propuesto, no creado |
| Alertas y notificaciones | Configuración de Cloud Monitoring / Cloud Logging | Propuesto, no creado |
| Exportadores Prometheus, Sentry o terceros | Ninguno activado por esta fase | No implementado |

La arquitectura evita un servidor de métricas adicional. En Cloud Run, cada contenedor conserva su propio agregado en memoria; para una visión global deben usarse los logs estructurados. El endpoint interno de métricas no está expuesto anónimamente y no sustituye a un sistema de series temporales.

## 2. Configuración

| Variable | Valor por defecto | Uso |
|---|---|---|
| `APP_ENV` | `development` | Se incluye en cada log como `environment`; valores permitidos: `development`, `staging`, `production`, `test`. |
| `LOG_LEVEL` | `INFO` | Nivel mínimo del root logger y de los loggers de Uvicorn; valores permitidos: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`. Un valor inválido falla la validación de entorno y el runtime usa `INFO` para no detener el proceso por configuración de observabilidad. |

`LOG_LEVEL` se valida en `src/securecode/config.py`, se aplica en `src/securecode/observability.py` y se configura en `.env.example`, `docker-compose.yml`, `Dockerfile`/Cloud Run y `README.md`. La validación no imprime secretos.

## 3. Formato de log

Cada línea de log es un objeto JSON con los campos obligatorios:

```json
{
  "timestamp": "2026-11-21T19:00:00.000Z",
  "level": "INFO",
  "event": "http.request",
  "service": "securecode",
  "environment": "production",
  "request_id": "9f2c1b7a4d8e4f6b"
}
```

Campos adicionales permitidos por el formateador: `method`, `route`, `status_code`, `duration_ms`, `error_type`, `control_id`, `result_status`, `outcome`, `reason`, `phase`, `operation`, `from_cache`, `check` y `attempt`.

Reglas de privacidad:

- El formateador usa una lista de campos permitidos; no emite `message`, bodies, encabezados ni objetos arbitrarios.
- Se descartan valores que parezcan JWT, URLs con esquema, o que contengan `password`, `secret`, `token`, `authorization` o `cookie`.
- Las rutas se normalizan: los parámetros `{}` se conservan como plantilla y los UUID se sustituyen por `{}`. Nunca se registran rutas crudas con identificadores.
- No se registran correos, nombres de usuario, identifiers de organización/repositorio, JWT, cookies CSRF ni cadenas `DATABASE_URL`.
- Las excepciones se registran por `error_type`; no se incluye `str(exception)` en los eventos de observabilidad.

## 4. Request ID y correlación

- Middleware: `ObservabilityMiddleware`, registrado como la capa más externa de la aplicación.
- Cabecera: `X-Request-ID`, permitida también en CORS.
- Validación: solo `[A-Za-z0-9_-]` con longitud de 1 a 64 caracteres. Cualquier otro valor se descarta y se genera un hexadecimal aleatorio de 32 caracteres.
- Contexto: `ContextVar` por solicitud; cada log de la solicitud comparte el mismo `request_id`.
- Respuesta: la cabecera `X-Request-ID` se devuelve en respuestas manejadas por el middleware, incluidas 4xx y 5xx gestionadas por FastAPI.
- Concurrencia: el contexto se fija y se restaura por solicitud; las pruebas cubren 20 tareas concurrentes.

## 5. Eventos emitidos

| Evento | Nivel | Cuando se emite |
|---|---|---|
| `http.request` | INFO | Toda solicitud con estado < 500. |
| `http.request.failed` | ERROR | Respuesta con estado >= 500. |
| `http.request.unhandled` | ERROR | Excepción no gestionada por un handler de aplicación; el cliente recibe 500 genérico. |
| `health.readiness.checked` | INFO/ERROR | Cada llamada a `/health/ready`, con `reason` genérico. |
| `database.readiness.failed` | ERROR | Fallo al verificar PostgreSQL en readiness; sin mensaje de excepción. |
| `configuration.readiness.failed` | ERROR | Configuración inválida detectada en readiness; sin valores de variables. |
| `evaluation.completed` | INFO | Evaluación persistida; `result_status` es `PASS`, `FAIL` o `UNKNOWN`. |
| `evaluation.technical_error` | ERROR | Fallo técnico de adquisición, evaluación o persistencia; `outcome=TECHNICAL_ERROR`. |
| `backup.operation.failed` | ERROR | Fallo del CLI de respaldo/verificación, con `operation`. |
| `backup.restore.failed` | ERROR | Fallo del CLI de restauración. |

`FAIL` y `UNKNOWN` son resultados de negocio y no se registran como errores. Las respuestas 401, 403 y 422 tampoco se consideran incidentes por defecto.

## 6. Health checks

| Endpoint | Objetivo | Comportamiento |
|---|---|---|
| `GET /health` | Compatibilidad con Dockerfile, CI y despliegues existentes | `200 {"status":"ok"}`, sin consultar PostgreSQL. |
| `GET /health/live` | Liveness de Cloud Run / orquestador | `200 {"status":"alive","service":"securecode"}`, sin dependencias externas. |
| `GET /health/ready` | Readiness antes de recibir tráfico | `200 {"status":"ready","reason":"ok"}` o `503 {"status":"not_ready","reason":"configuration_invalid|database_unavailable"}`. |

Readiness valida configuración y ejecuta `SELECT 1` con `SET LOCAL statement_timeout = 250ms`. Para PostgreSQL se usa `connect_timeout=2` segundos en el engine. No consulta GitHub ni realiza evaluaciones. No expone mensajes de SQL, nombre de base ni URL de conexión.

## 7. Métricas agregadas por proceso

`GET /internal/observability/metrics` requiere rol `platform_admin`. Devuelve:

- `http_requests_total`: etiquetas `method`, `route`, `status_class` (`2xx`, `3xx`, `4xx`, `5xx`, `unknown`).
- `http_request_duration_ms`: misma etiqueta base, `count`, `sum_ms` y buckets acumulados `le_50`, `le_100`, `le_250`, `le_500`, `le_1000`, `le_2500`, `le_5000`, `le_inf`.
- `evaluations_total`: etiquetas `control` (`GH-001`, `GH-002`, `GH-003`, `OTHER`), `result` (`PASS`, `FAIL`, `UNKNOWN`, `NONE`) y `outcome` (`RESULT`, `TECHNICAL_ERROR`, `OTHER`).
- `evaluation_duration_ms`: mismas etiquetas de evaluación con buckets de duración.

Todas las etiquetas están acotadas y no incluyen IDs de usuario, organización, repositorio ni evaluación. La ruta no coincidente se reporta como `unmatched`.

## 8. Propuesta de alertas (no activadas)

| Nombre | Condición propuesta sobre logs | Umbral / ventana | Severidad | Destinatario propuesto | Respuesta sugerida | Falso positivo a descartar |
|---|---|---|---|---|---|---|
| `SecureCode - 5xx elevado` | Count de `event="http.request.failed"` agrupado por `route` | > 5 eventos en 5 min | Crítico | Guardia de operación | Correlacionar `request_id`, revisar logs, rollback si coincide con despliegue | Pruebas de caos o tráfico de smoke controlado |
| `SecureCode - Excepción no gestionada` | Count de `event="http.request.unhandled"` | >= 1 en 5 min | Crítico | Guardia de operación | Revisar `error_type` y `request_id`; escalar a desarrollo | Una sola excepción aislada durante despliegue |
| `SecureCode - Readiness degradation` | Count de `event="database.readiness.failed"` | > 3 en 5 min | Crítico | Guardia de operación + DBA | Verificar PostgreSQL y pool; suspender transferencia de tráfico | Mantenimiento planificado de la base |
| `SecureCode - Errores técnicos de evaluación` | Count de `event="evaluation.technical_error"` agrupado por `control` | > 5 en 10 min | Alto | Operación + dueño de integración GitHub | Revisar `error_type`; comprobar token y disponibilidad de GitHub | `FAIL` o `UNKNOWN`, que no generan este evento |
| `SecureCode - Fallo de respaldo` | Count de `event="backup.operation.failed"` o `event="backup.restore.failed"` | >= 1 inmediato | Crítico | DBA | Detener ciclo, revisar `operation` y `error_type`, ejecutar verificación sintética | Ejecución manual cancelada deliberadamente |
| `SecureCode - 4xx inusual` | Rate de `event="http.request"` con `status_class="4xx"` | > 50 % en 10 min, mínimo 20 solicitudes | Medio | Operación | Revisar cambios de auth/CORS y tráfico entrante | Escaneo externo o campaña de login legítima fallida |
| `SecureCode - Latencia HTTP` | Percentil aproximado desde buckets de `http_request_duration_ms` | p95 > 1500 ms en 10 min | Medio | Operación | Comparar por `route`, revisar DB y GitHub | Carga de prueba o cold start aislado |

La conversión de eventos a métricas, la política de notificación y la creación de canales requieren autorización explícita. Este repositorio solo entrega los eventos y la propuesta parametrizada.

## 9. FinOps y retención

- Volumen: una línea `http.request` por solicitud manejada y una línea adicional por error crítico o evaluación. Los sondeos de health también generan logs; si el volumen es alto, filtrar `route="/health*"` en el sink, conservando `http.request.failed`.
- Cardinalidad: limitada por plantillas de ruta, clases de estado, tres controles canónicos y tipos de error. No se usan IDs como etiqueta.
- Muestreo: no hay muestreo activo en la aplicación. La política recomendada es conservar el 100 % de errores, evaluaciones y respaldos; aplicar muestreo solo a `http.request` exitoso si el costo lo exige.
- Retención: definir en la configuración del proveedor, no en código. Valor propuesto a revisar: 30 días para logs operacionales y 90 días para auditoría de errores críticos.
- Costo: depende del volumen de ingestión, retención, consultas y exportación del proveedor. No se incluyen precios ni estimaciones monetarias porque no hay datos contractuales verificables.
- Agregados en memoria: no persisten tras reinicio y no se consolidan entre réplicas. Consultar el endpoint por instancia solo para diagnóstico local; usar logs para reporting global.

## 10. Verificación local

```bash
python -m pytest -q tests/api/test_observability.py tests/unit/test_observability_backup_errors.py
python -m pytest -q
mypy src
ruff check src tests scripts
git diff --check
```

Criterios observables:

- `/health`, `/health/live` y `/health/ready` responden según la sección 6.
- `X-Request-ID` se devuelve y se correlaciona en logs.
- Los logs son JSON de una sola línea y no contienen secretos ni rutas crudas.
- `/internal/observability/metrics` rechaza acceso anónimo y no muestra identificadores sensibles.
- `FAIL` y `UNKNOWN` no generan logs ERROR; un `RuntimeError` de GitHub sí genera `evaluation.technical_error`.

Resultados de la validación Fase 12 del 2026-11-21:

- `pytest -q` sin PostgreSQL: 358 aprobadas / 20 omitidas.
- `pytest -q` con PostgreSQL aislado y `REQUIRE_POSTGRES_TESTS=1`: 378 aprobadas.
- `mypy src`: sin errores en 31 archivos fuente.
- `ruff check` sobre los archivos nuevos y modificados por observabilidad: sin hallazgos.
- `ruff check src tests scripts`: 220 hallazgos preexistentes fuera de Fase 12.
- `git diff --check`: sin errores de espaciado.
