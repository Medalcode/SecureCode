# SecureCode — Documentación de entrega ES3

Conjunto de manuales de la entrega ES3 del proyecto SecureCode. La documentación fue elaborada a partir de la revisión directa del código fuente, de la suite de pruebas del repositorio y de auditorías funcionales ejecutadas contra la instancia de producción. Cada afirmación operativa es trazable a una fuente; lo que no pudo comprobarse en esta entrega se declara explícitamente como **pendiente de validación**.

## Contenido

| Documento | Descripción | Audiencia principal |
|---|---|---|
| [01-manual-de-usuario.md](01-manual-de-usuario.md) | Uso completo de la plataforma: sitio público, registro, consola, evaluación de controles, evidencia, informe de gestión, plan/SLA, FinOps y organización. | Usuarios finales (Owner, Analyst, Administrador TI) y evaluadores de la demo |
| [02-manual-administracion-operacional.md](02-manual-administracion-operacional.md) | Operación del servicio: variables de entorno, seguridad, límites, gestión de cuentas, datos no conectados y procedimientos operacionales. | Equipo de operación y Administrador TI |
| [03-guia-demo.md](03-guia-demo.md) | Guion de demostración presencial y de video (12–15 minutos), con checklist de preparación y campos de contexto académico a completar. | Integrantes del equipo que presentan |
| [04-matriz-evidencia.md](04-matriz-evidencia.md) | Matriz de evidencia y trazabilidad: validaciones locales, auditorías de producción, mapeo funcionalidad → fuente → prueba → estado. | Profesor evaluador y equipo |
| [05-respaldos-y-recuperacion.md](05-respaldos-y-recuperacion.md) | Política propuesta, respaldo portable, restauración aislada, verificación sintética, incidentes y automatización no activada. | Equipo de operación y DBA |
| [06-observabilidad.md](06-observabilidad.md) | Logs JSON, request ID, métricas por proceso, health checks, propuesta de alertas y FinOps de telemetría. | Equipo de operación, DBA y soporte |
| [STAGING-001.md](../specs/STAGING-001.md) | Arquitectura staging propuesta, plantilla Cloud Run, matriz de alertas, pipeline de release, FinOps y runbook de rollback. | DevSecOps, SRE y DBA |
| [STAGE13-READINESS.md](../specs/STAGE13-READINESS.md) | Informe final de preparación: Git, build, PostgreSQL, E2E, benchmarks, seguridad, matriz de readiness y veredicto. | Dirección, QA, DevSecOps y revisión contractual |

## Alcance y convenciones

- **Roles documentados** (únicos roles del sistema): `organization_owner` (Propietario de la organización), `analyst` (Analista) y `platform_admin` (Administrador TI).
- **Controles canónicos** (catálogo servido por `/api/v1/rules`, versión de catálogo `1`): `GH-001` (política de revisión de rama), `GH-002` (protección de rama por defecto), `GH-003` (exigencia de commits firmados).
- **Estados de evaluación**: `PASS` (conforme), `FAIL` (no conforme), `UNKNOWN` (la evidencia disponible no permite probar cumplimiento ni incumplimiento).
- **No facturable**: la plataforma es una demostración académica. La facturación, la telemetría de CI y las métricas de rendimiento en vivo aparecen como `not_connected` / `not_live` tanto en el código como en la interfaz; esta documentación respeta ese estado y no declara métricas comerciales ni de operación que el sistema no emite.
- **Notación**: los ítems marcados **[pendiente de validación]** no pudieron verificarse en esta entrega. No se incluyen contraseñas, secretos ni credenciales de ningún tipo en esta documentación.
- Los nombres de vistas, botones y campos corresponden al código de la interfaz (`src/securecode/static/`) vigente en el árbol de trabajo local al momento de escribir estos manuales.

## Estado de validación global

| Ámbito | Estado |
|---|---|
| Suite de pruebas local (unitarias + API + SQLite) | Validada: 358 aprobadas / 20 omitidas (marcadas `postgres`, requieren base PostgreSQL); con PostgreSQL aislado: 378 aprobadas |
| Análisis estático (`mypy`, `compileall`, `node --check`, `git diff --check`) | Validado |
| Auditoría funcional en producción (API) | Validada en esta entrega: 10 verificaciones PASS / 0 FAIL (ver matriz 04) |
| Auditoría del flujo de restablecimiento de contraseña en producción | Validada en esta entrega: 19/19 pasos PASS |
| Funcionalidad "Informe de Gestión" | Validada en producción: desplegada en la revisión `securecode-00046-94s` (100 % del tráfico), bundle `20261118-management-report` y `/health` = `ok`. Acceso restringido al rol `Organization Owner` |
| Operación de infraestructura (despliegue, respaldos, monitoreo) | Despliegue verificado: revisión activa `securecode-00046-94s` con 100 % del tráfico y `/health` = `ok`. Respaldo y restauración validados en PostgreSQL aislado con datos sintéticos; observabilidad local implementada y probada en el árbol de trabajo. Programación cloud, cobertura real de Supabase, pipeline de despliegue, métricas globales y alertas externas **pendientes de validación** |

## Hallazgos para revisión del equipo

Incoherencias y pendientes detectados durante la elaboración de estos manuales. No se corrigió ninguno (el encargo ES3 prohíbe modificar código):

1. **Cambios sin confirmar en `main`**: el árbol de trabajo contiene modificaciones sin commit en `src/securecode/api/app.py`, `src/securecode/static/index.html`, `src/securecode/static/js/app.js`, `src/securecode/static/css/app.css`, `tests/api/test_frontend_routes.py` y `tests/api/test_organization_roles_http.py`. La funcionalidad correspondiente (páginas públicas + informe de gestión) ya está desplegada en producción (revisión `securecode-00046-94s`); el árbol local conserva copias sin confirmar.
2. **Mojibake preexistente**: 29 líneas de `app.py` contienen caracteres UTF-8 corruptos (defecto conocido, ya integrado y en producción; fuera del alcance de ES3).
3. **Canal comercial y de contacto pendientes**: la página `/contacto` declara que el correo corporativo, el responsable de privacidad y el domicilio de notificación no están configurados. Es una limitación declarada por el propio producto, no un defecto.
4. **Facturación no conectada**: `billing_data_state` es siempre `not_connected` y `observed_spend_clp` siempre nulo; los montos de planes son proyecciones del informe ES2. Los manuales lo indican en cada vista afectada.
5. **Convención de versionado de bundles**: los sufijos de bundle incorporan una fecha (p. ej. `20261118-management-report`); se sugiere documentar la convención y usar la revisión de Cloud Run (`securecode-00046-94s`) como referencia del despliegue vigente.
6. **13 pruebas omitidas** requieren PostgreSQL/Supabase; con SQLite se ejecutan 233. Para la demo se recomienda correr la suite completa contra la base de integración. [pendiente de validación]

## Fuentes de verificación

- Código: `src/securecode/api/app.py`, `src/securecode/api/security.py`, `src/securecode/api/dependencies.py`, `src/securecode/api/public_site.py`, `src/securecode/engine/`, `src/securecode/static/`.
- Pruebas: `tests/unit/`, `tests/api/`, `tests/integration/` (37 archivos con pruebas).
- Documentación previa conservada: `docs/SECURECODE_Informe_ES2_AVANCE_FINAL_CORREGIDO.md`, `docs/evidence/`.
- Auditorías ejecutadas en esta entrega contra `https://securecode-n43etfo4dq-uc.a.run.app` (detalle en `04-matriz-evidencia.md`).
- Verificación de despliegue: revisión activa de Cloud Run `securecode-00046-94s` con 100 % del tráfico, HTML de `/app` conteniendo el bundle `20261118-management-report` y `GET /health` = `ok`.

Los manuales se actualizan cuando cambia el estado verificable del sistema; este índice refleja la versión vigente del árbol de trabajo.
