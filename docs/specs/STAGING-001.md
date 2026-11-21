# STAGING-001 — Preparación de staging, release y recuperación

## 1. Estado de esta especificación

Este documento es una preparación, no una ejecución. No se crearon servicios Cloud Run, bases, secretos, cuentas de servicio, alertas, presupuestos ni reglas de firewall. La plantilla `deploy/staging/cloud-run-service.yaml` no ha sido aplicada.

Clasificación usada en este documento:

- **VERIFICADA**: comprobada en este repositorio o en ejecuciones locales de esta fase.
- **PROPUESTA**: diseño preparado, sin recurso cloud creado.
- **NO VERIFICADA**: no hay evidencia suficiente.
- **BLOQUEANTE**: impide declarar preparación para producción.

## 2. Arquitectura de staging propuesta

| Componente | Diseño | Estado |
|---|---|---|
| Servicio Cloud Run | `securecode-staging`, región a definir, imagen por digest, sin tráfico productivo | PROPUESTA |
| Base de datos | Instancia PostgreSQL exclusiva de staging; nombre y proyecto a definir; sin datos reales | PROPUESTA |
| Secretos | Secretos exclusivos: `securecode-staging-database-url`, `securecode-staging-jwt-secret`, `securecode-staging-github-token` | PROPUESTA |
| Cuenta de servicio | `REPLACE_WITH_STAGING_SA`, sin roles de producción; acceso solo a secretos de staging y a la base de staging | PROPUESTA |
| HTTPS | TLS administrado por Cloud Run; `CORS_ORIGINS=https://staging.example.invalid` | PROPUESTA |
| Identidad | Acceso IAM al servicio de staging; no reutilizar identidad de producción | PROPUESTA |
| Logs | `APP_ENV=staging` y `LOG_LEVEL=INFO`; aggregation por etiqueta `environment=staging` | PROPUESTA |
| Recursos | `minScale=0`, `maxScale=2`, CPU `1`, memoria `512Mi`, concurrencia `40`, timeout `60s` | PROPUESTA |
| Datos | Solo datos sintéticos creados por pruebas y scripts de verificación | PROPUESTA |
| Smoke | Workflow manual `candidate-smoke.yml` existente; requiere URL y credenciales de candidato | VERIFICADA en repositorio |

La plantilla declarativa está en `deploy/staging/cloud-run-service.yaml`. No contiene valores reales de proyecto, cuenta de servicio, secrete ni imagen.

## 3. Variables de entorno de staging

| Variable | Valor o mecanismo | Clasificación |
|---|---|---|
| `APP_ENV` | `staging` | PROPUESTA |
| `DATABASE_URL` | Secreto exclusivo de staging | PROPUESTA |
| `JWT_SECRET_KEY` | Secreto exclusivo de staging, longitud mínima 32 | PROPUESTA |
| `GITHUB_TOKEN` | Secreto exclusivo de staging; token de validación no perteneciente a clientes | PROPUESTA |
| `CORS_ORIGINS` | Origen HTTPS explícito de staging, sin `*` | PROPUESTA |
| `LOG_LEVEL` | `INFO` | PROPUESTA |
| `JWT_ALGORITHM` | `HS256` | VERIFICADA en código |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | PROPUESTA |
| `LOGIN_MAX_FAILURES` | `5` | PROPUESTA |
| `LOGIN_WINDOW_SECONDS` | `900` | PROPUESTA |
| `TRUST_PROXY_HEADERS` | `true` | PROPUESTA |
| `PORT` | `8080` en la plantilla; Cloud Run inyecta el puerto dinámico real | PROPUESTA |

La validación de arranque en `src/securecode/config.py` rechaza placeholders y SQLite fuera de `development`/`test`.

## 4. Seguridad de despliegue

| Requisito | Clasificación | Evidencia o acción pendiente |
|---|---|---|
| Secret Manager | PROPUESTA | Secrets separados por entorno; no se crearon. |
| Cuenta de servicio | PROPUESTA | Principio de mínimo privilegio; no se creó. |
| Acceso a PostgreSQL | PROPUESTA | Solo desde el servicio de staging; pendiente de implementación cloud. |
| CORS | VERIFICADA en código | `CORS_ORIGINS` exige HTTPS y rechaza `*` en staging/production. |
| HTTPS | PROPUESTA | Cloud Run administra TLS; no se comprobó un servicio real de staging. |
| CSP | VERIFICADA en código | Middleware de cabeceras de seguridad en `src/securecode/api/app.py`. |
| HSTS | PROPUESTA | Depende del balanceador/gateway; no verificado en Cloud Run. |
| Cookies | VERIFICADA localmente | HttpOnly, SameSite=Lax y `Secure` cuando HTTPS/`APP_ENV` staging/production; E2E de navegador aprobado. |
| Variables de entorno | VERIFICADA en código | Validación centralizada en `src/securecode/config.py`. |
| Rate limiting | PARCIAL | Bloqueo local por usuario/alcance verificado; rate limiting distribuid requiere gateway o proveedor. |
| Límites de recursos | PROPUESTA | Definidos en la plantilla; no aplicados. |
| Exposición pública | PROPUESTA | Staging debe usar IAM; no se creó política de acceso. |
| Control administrativo | VERIFICADA | Rutas `/api/v1/admin/*` exigen `platform_admin`. |
| Imagen sin secretos | VERIFICADA estáticamente | Dockerfile no copia `.env`; `.dockerignore` lo excluye. No se pudo construir por daemon Docker caído. |

## 5. Matriz de alertas propuesta

No existe evidencia de alertas creadas en Cloud Monitoring. Todo lo siguiente está **PENDIENTE DE AUTORIZACIÓN**.

| Alerta | Señal | Umbral propuesto | Respuesta inicial | Estado |
|---|---|---|---|---|
| HTTP 5xx | `http.request.failed` con `status_code>=500` | >1 en 5 min por servicio | Revisar logs JSON y request ID; revisar úlcera de evaluación | PROPUESTA |
| Latencia HTTP | `http_request_duration_ms` | P95 >1000 ms durante 10 min | Revisar saturación, concurrencia y dependencias | PROPUESTA |
| Fallo PostgreSQL | `database.readiness.failed` | Cualquier evento | Verificar conectividad, secretos y pool | PROPUESTA |
| Readiness | `/health/ready` 503 | 2 consecutivos | Drenar instancia y revisar configuración/base | PROPUESTA |
| Errores de evaluación | `evaluation.technical_error` | >3 en 15 min | Revisar GitHub adapter y token | PROPUESTA |
| Fallos de respaldo | `backup.operation.failed` | Cualquier evento | Detener automatización, revisar manifiesto y permisos | PROPUESTA |
| Fallos de restauración | `backup.restore.failed` | Cualquier evento | No promover candidato; escalar a DBA | PROPUESTA |

La app emite eventos y métricas por proceso; los agregados no sobreviven a reinicios ni se consolidan entre réplicas. La conversión a métricas globales requiere configuración de proveedor.

## 6. Pipeline de release controlado

1. Validar Git: rama, HEAD, cambios locales y lista de release del informe `STAGE13-READINESS.md`.
2. Ejecutar `pytest -q`, suite PostgreSQL, mypy, Ruff y `git diff --check`.
3. Verificar migraciones en base aislada: `alembic upgrade head`, `alembic current`, `alembic check`.
4. Construir imagen por digest con Dockerfile; bloqueo actual: daemon Docker no disponible.
5. Escanear dependencias e imagen; no hay evidencia de escaneo ejecutado.
6. Publicar candidato a Artifact Registry solo con autorización.
7. Migrar base de staging de forma controlada; nunca ejecutar migración productiva desde esta fase.
8. Ejecutar smoke tests HTTPS con `candidate-smoke.yml`.
9. Verificar cabeceras, sesión, CSRF, health y logs sin secretos.
10. Activar monitoreo y alertas propuestas solo después de autorización.
11. Aprobación humana obligatoria antes de producción.
12. Transferencia progresiva de tráfico por revisiones de Cloud Run.
13. Ejecutar rollback si falla cualquier compuerta.

No se agregó ningún workflow de despliegue automático a producción.

## 7. Runbook de rollback

### A. Rollback de aplicación

- Acción: seleccionar revisión anterior de Cloud Run con `--to-revisions <REVISION>=100`.
- No modifica PostgreSQL.
- Requiere confirmar que la revisión anterior es compatible con el esquema actual.
- Validación local: se creó un worktree detached en `51beb05`; la aplicación anterior importó correctamente y consultó una base con esquema `d4e9f1a2b3c4`. No se desplegó ni se cambió tráfico.

### B. Rollback de base de datos

- No asumir que rollback de Cloud Run revierte Alembic.
- `alembic downgrade d4e9f1a2b3c4:c3f8a1d6e902 --sql` se generó sin ejecutarse: el SQL elimina `user_sessions.csrf_token_hash` y luego la tabla `user_sessions`.
- La bajada a revisiones anteriores elimina tablas o columnas con datos de sesiones, aceptaciones, auditorías y preferencias. Por eso está clasificada como **POTENCIALMENTE DESTRUCTIVA** y no se ejecutó.
- Si un incidente exige volver el esquema, primero restaurar un respaldo lógico verificado en una base nueva y validar recuentos e integridad referencial.
- No promover una reversión de esquema sin aprobación de DBA y evaluación de pérdida de datos.

## 8. FinOps

| Recurso | Estado | Acción de control |
|---|---|---|
| Cloud Run | PROPUESTO para staging | `maxScale=2`, concurrencia 40, CPU 1, memoria 512Mi, `minScale=0`. |
| PostgreSQL | PROPUESTO para staging | Tamaño y plan a definir; sin recursos creados. |
| Respaldo | VERIFICADO localmente | Medición local: 2,692 s backup y 0,833 s restore; no equivale a RPO/RTO cloud. |
| Secret Manager | PROPUESTO | Tres secretos de staging; sin creación. |
| Cloud Logging | PROPUESTO | Retención sugerida ya documentada en manual 06; no aplicada. |
| Cloud Monitoring | PROPUESTO | Alertas matrices en sección 5; no creadas. |
| Artifact Registry | PROPUESTO | Publicar por digest y limpiar candidatos obsoletos tras aprobación. |
| Tráfico de red | NO MEDIDO | Requiere datos reales de staging. |
| Costos monetarios | NO MEDIDOS | No se inventan precios ni consumo. |

La facturación de producto permanece `not_connected` y no se crearon presupuestos ni compromisos económicos.

## 9. Cierre de autorizaciones

Las acciones cloud siguientes quedan explícitamente pendientes de autorización: creación de proyecto/servicios/base/secretos/cuenta de servicio, publicación de imagen, activación de alertas, apply de la plantilla, migración en staging y transferencia de tráfico. Esta fase no ejecutó ninguna.
