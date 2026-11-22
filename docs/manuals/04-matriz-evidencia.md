# Matriz de evidencia y trazabilidad — SecureCode (ES3)

Matriz que respalda la entrega ES3: validaciones ejecutadas, auditorías de producción y trazabilidad entre funcionalidades documentadas, su fuente en el código y su prueba. Los estados posibles de la matriz son **Validado** (comprobado en esta entrega) y **Pendiente de validación**.

## 1. Validaciones locales ejecutadas (árbol de trabajo al 2026-11-16)

| Validación | Comando / método | Resultado | Estado |
|---|---|---|---|
| Suite de pruebas (unitarias + API + SQLite) | `pytest` sobre `tests/` | 233 aprobadas / 13 omitidas (omitidas marcadas `postgres`) | Validado |
| Análisis de tipos | `mypy` sobre el paquete | Sin errores (22 archivos fuente) | Validado |
| Compilación Python | `compileall` sobre `src/` | Sin errores | Validado |
| Sintaxis JavaScript | `node --check` sobre `src/securecode/static/js/app.js` | Sin errores | Validado |
| Higiene del árbol Git | `git diff --check` | Sin conflictos de espacios | Validado |

Las 13 pruebas omitidas corresponden a `tests/integration/test_postgres_integration.py` (8), `test_gh002_postgres.py` (1) y `test_migrations.py` (4), que requieren PostgreSQL. **[pendiente de validación: ejecución de la suite completa contra la base PostgreSQL/Supabase de integración]**

## 2. Auditorías de producción ejecutadas en esta entrega

Contra `https://securecode-n43etfo4dq-uc.a.run.app` mediante su API pública. Las credenciales usadas fueron cuentas de prueba autorizadas y no se registran en este documento.

### 2.1 Auditoría funcional (roles, autorizaciones y evaluación)

Resultado: **10 verificaciones PASS / 0 FAIL / 0 bloqueos**.

| # | Verificación | Resultado observado |
|---|---|---|
| 1 | Creación de Analyst con contraseña temporal generada | Alta exitosa; temporal entregada una sola vez, no persistida |
| 2 | Inicio de sesión del Analyst con la temporal | Token emitido, rol `analyst` correcto |
| 3 | Autorización de repositorio por el Propietario (`medalcode/securecode`) | Autorización registrada |
| 4 | Evaluación GH-002 del repositorio autorizado | PASS; evidencia persistida con huella SHA-256 (`b1e1a72d…`) |
| 5 | Formato de repositorio inválido | 422 "El repositorio debe usar el formato owner/repo" |
| 6 | Evaluación de repositorio no autorizado (`facebook/react`) | 403 en ~0.4 s; sin evidencia persistida |
| 7 | Revocación de la autorización por el Propietario | Revocación efectiva e inmediata |
| 8 | Evaluación tras revocación | 403 para el Analyst |
| 9 | Acceso de Analyst a FinOps / suscripción / administración | 403 en los tres casos (autorización server-side) |
| 10 | Estado de la sesión tras cierre de sesión | Sesión revocada y cookies eliminadas; `localStorage` conserva solo preferencias y datos de visualización |

### 2.2 Auditoría del flujo de restablecimiento de contraseña

Resultado: **19/19 pasos PASS**, ejecutada contra la revisión que incluía el fix de UX de contraseñas (`20261117-analyst-password-ux`), predecesora de la revisión vigente `securecode-00046-94s`. Puntos verificados:

- Restablecimiento con temporal generada: contraseña única no persistente; inicio de sesión del Analyst con la temporal correcto.
- Restablecimiento con contraseña definida: la respuesta no reporta `temporary_password`.
- Una temporal ya aplicada/invalidada deja de autenticar: 401 `{"detail": "Incorrect username or password"}`.
- Rechazos 403 exactos del Analyst en módulos restringidos (FinOps, suscripción, administración).
- `localStorage` del navegador no contiene JWT ni `securecode_token`; la sesión se transporta en cookie HttpOnly y el CSRF se envía por cabecera.
- Nota de incidente gestionado en la auditoría: un restablecimiento se aplicó por error a una cuenta de auditoría distinta de la objetivo; se remedió en la misma sesión estableciendo una contraseña equivalente y se documentó. Sin impacto sobre datos de organizaciones.

### 2.3 Verificación de estado de despliegue (2026-11-16)

| Sondeo | Resultado | Interpretación |
|---|---|---|
| Tráfico de Cloud Run | 100 % dirigido a la revisión `securecode-00046-94s` | Despliegue único y vigente; sin tráfico dividido entre revisiones |
| `GET /health` | `ok` | Servicio en línea |
| `GET /app` | 200; el HTML contiene el bundle `20261118-management-report` | La producción publicada incluye la vista "Informe de Gestión" |

Notas de esta verificación: es documental (sondeos y HTML publicado), no incluye prueba de carga ni interacción autenticada; el acceso al informe exige sesión del rol `Organization Owner` (la vista está oculta para otros roles y el servidor aplica 403 por defecto, verificado con las auditorías 2.1 y 2.2).

## 3. Inventario de pruebas del repositorio

37 archivos con pruebas, contados con búsqueda de definiciones (`rg -c "def test_" tests`). El total de ejecución (233/13) proviene de `pytest` y difiere del conteo de definiciones porque existen casos parametrizados.

| Grupo | Archivos | Enfoque |
|---|---|---|
| Motor y evaluación | `test_executor.py` (10), `test_gh001_evaluator.py` (12), `test_gh002_evaluator.py` (4), `test_gh002_status_matrix.py` (1), `test_gh003.py` (3), `test_evaluate_and_store.py` (2), `test_evaluation_request_validation.py` (3), `test_validation_runner.py` (2) | Lógica trivalente PASS/FAIL/UNKNOWN, controles GH-001/002/003, almacenamiento de evaluaciones |
| Adaptadores e integración GitHub | `test_github_adapter.py` (12), `test_github_client_isolation.py` (6), `test_mock_github.py` (3), `test_gh002_adapter.py` (4) | Evidencia de repositorio/rama, aislamiento de cliente |
| Seguridad | `test_argon2id_policy.py` (8), `test_security.py` (9), `test_hashing.py` (3), `test_login_rate_limit.py` (2), `test_authorization.py` (2) | Argon2id, tokens, límite de tasa, autorización |
| API HTTP | `test_app.py` (8), `test_auth.py` (8), `test_organization_roles_http.py` (14), `test_user_management.py` (6), `test_repository_authorization.py` (5), `test_admin_http.py` (4), `test_gh002_app.py` (4), `test_subscription.py` (3), `test_finops.py` (2), `test_client_settings.py` (3), `test_enterprise_trial_http.py` (5), `test_frontend_routes.py` (10), `test_security_headers.py` (1) | Registro, roles, gestión de cuentas, autorizaciones, suscripción, FinOps, configuración, prueba enterprise, rutas frontend y cabeceras |
| Integración | `test_sqlite_integration.py` (6), `test_postgres_integration.py` (8), `test_gh002_postgres.py` (1), `test_migrations.py` (4) | Persistencia; PostgreSQL requerido en los 3 últimos (13 omitidas sin base) |
| Desempeño y despliegue | `test_measure_local_performance.py` (5), `test_deploy002_config.py` (21) | Mediciones controladas; configuración de despliegue |

## 4. Trazabilidad funcionalidad → fuente → prueba → estado

| Funcionalidad documentada | Fuente principal | Respaldo | Estado |
|---|---|---|---|
| Sitio público (portada, nosotros, contacto, FAQ, 6 documentos legales) | `src/securecode/api/public_site.py`, `app.py` (rutas públicas) | `test_frontend_routes.py`; navegación verificada en producción | Validado |
| Registro de organización + propietario | `app.py` (`OrganizationRegistrationRequest`) | `test_auth.py`, `test_app.py` | Validado |
| Inicio de sesión, JWT, límite de tasa | `src/securecode/api/security.py`, `app.py` | `test_auth.py`, `test_login_rate_limit.py`, `test_security.py` | Validado |
| Evaluador GH-001/GH-002/GH-003 con PASS/FAIL/UNKNOWN | `src/securecode/engine/` (executor), reglas JSON, `/api/v1/rules` | Pruebas de motor y adaptadores; auditoría 2.1 (#4, #6) | Validado |
| Evidencia con huella SHA-256 y verificación pública | `app.py` (`/api/v1/verify/{id}`, `/api/v1/evaluations/*`) | Auditoría 2.1 (#4); FAQ pública lo declara | Validado |
| Historial y exportación CSV | `app.js` (`btnExportHistory`) | Revisión de código; comportamiento en producción | Validado |
| Alta/edición de Analysts, temporal de un solo uso, semántica de campo vacío | `app.py` (miembros), `app.js` (modal de restablecimiento) | `test_organization_roles_http.py`, `test_user_management.py`; auditoría 2.2 | Validado |
| Autorización/revocación de repositorios por Analyst | `app.py` (repository-authorizations) | `test_repository_authorization.py`; auditoría 2.1 (#3, #5–#8) | Validado |
| Control de permisos server-side (403 por rol) | Dependencias de sesión/rol en `app.py` | Auditorías 2.1 (#9) y 2.2 | Validado |
| Informe de gestión (API + vista + CSV + impresión) | `app.py` (`/api/v1/management-report`), `index.html`, `app.js` | Pruebas locales; despliegue verificado (sección 2.3): revisión `securecode-00046-94s` con 100 % del tráfico, bundle `20261118-management-report`, `/health` = `ok` | Validado |
| Consumo & FinOps (presupuesto, umbral, alerta; facturación no conectada) | `app.py` (`FinOpsResponse`), vista de consumo | `test_finops.py`; insignia "SIN CONEXIÓN" en interfaz | Validado |
| Plan & SLA (catálogo Pro/Premium, cambio con confirmación, marco ITIL v4) | `app.py` (catálogo de planes, suscripción), `index.html` | `test_subscription.py` | Validado |
| Prueba Enterprise técnica no facturable | `app.py` (`enterprise-trial`) | `test_enterprise_trial_http.py`, `test_enterprise_trial.py` | Validado |
| Configuración del cliente (repositorio/rama por defecto, idioma, tema, notificaciones) | `app.py` (`/api/v1/settings`) | `test_client_settings.py` | Validado |
| Consola de administración y estado del sistema (CI/performance `not_connected`/`not_live`, SLA de referencia) | `app.py` (`/api/v1/system/overview`, `/api/v1/admin/users`) | `test_admin_http.py` | Validado |
| Seguridad de cabeceras y `no-store` | `SecurityHeadersMiddleware`, rutas HTML | `test_security_headers.py`, `test_frontend_routes.py` | Validado |
| Despliegue y health check | — | Verificación de despliegue (sección 2.3): revisión `securecode-00046-94s` con 100 % del tráfico, `/health` = `ok`, bundle `20261118-management-report` | Validado |
| Pipeline de despliegue, respaldos y monitoreo externo | — (no evidenciado en el repositorio) | — | **Pendiente de validación** |
| Ejecución de suite completa contra PostgreSQL/Supabase | — | — | **Pendiente de validación** |
| Contexto académico de la demo (integrantes, RUT, enlace al video) | — | Campos a completar en `03-guia-demo.md` | **Pendiente de validación** |

## 5. Evidencias de entregas previas (referencia, sin modificar)

- `docs/SECURECODE_Informe_ES2_AVANCE_FINAL_CORREGIDO.md` — informe de avance ES2 (base de las proyecciones comerciales citadas en la vista de planes).
- `docs/evidence/` — carpeta de evidencias previas (controles de gobernanza con JSON de evidencia, anexos técnicos y registros P0–P4 de noviembre de 2026).

## 6. Limitaciones de esta matriz

- Las auditorías de producción se ejecutaron por API y lectura de interfaz; no incluyen pruebas de carga ni de penetración.
- El porcentaje de conformidad del informe de gestión se calcula sobre dictámenes concluyentes (PASS+FAIL); los UNKNOWN no lo afectan, y con cero dictámenes se informa "—" (sin valor).
- Los conteos por archivo de la sección 3 provienen de inspección estática y no sustituyen la ejecución de `pytest` con la base PostgreSQL para el subconjunto omitido.
