# Manual de administración operacional — SecureCode (ES3)

Manual de operación del servicio SecureCode orientado al equipo de operación y al Administrador TI. Contenido verificado contra el código fuente al 2026-11-21; los aspectos de infraestructura no comprobables desde el repositorio se marcan como **pendiente de validación**.

## 1. Composición del servicio

| Componente | Descripción | Fuente |
|---|---|---|
| API | Aplicación FastAPI (`src/securecode/api/app.py`) con API interactiva en `/docs` (OpenAPI). | Código |
| Interfaz | Shell de aplicación estática servido en `/app` (con `Cache-Control: no-store`), más sitio público en `/`, `/nosotros`, `/contacto`, `/preguntas-frecuentes` y `/legal/{document}`. | Código |
| Archivos estáticos | Montados bajo `/static` desde `src/securecode/static`. | Código |
| Base de datos | PostgreSQL. La variable `DATABASE_URL` es obligatoria; el adaptador contempla entornos con PostgreSQL administrado (p. ej. Supabase, según comentario del adaptador). | Código |
| Adaptador GitHub | Consulta la evidencia de repositorios/ramas vía API de GitHub; usa el token de `GITHUB_TOKEN` si está definido. | Código |
| Motor de evaluación | `src/securecode/engine/` — lógica trivalente (PASS/FAIL/UNKNOWN) sobre catálogo de reglas JSON en `src/securecode/engine/rules/`. | Código |

Instancia de producción: `https://securecode-n43etfo4dq-uc.a.run.app` (consola: `https://securecode-n43etfo4dq-uc.a.run.app/app`). Revisión activa de Cloud Run: `securecode-00046-94s`, con el 100 % del tráfico dirigido a ella y `GET /health` respondiendo `ok`. Procedimiento de respaldo/restauración validado en PostgreSQL aislado con datos sintéticos; programación cloud, cobertura real del proveedor y monitoreo externo **pendientes de validación**.

## 2. Variables de entorno

Todas verificadas en el código. Sin ellas o con valores inválidos, el servicio no parte o degrada el comportamiento indicado.

| Variable | Requerida | Por defecto | Efecto |
|---|---|---|---|
| `APP_ENV` | Sí en arranque validado | `development` | Entorno lógico; valores permitidos: `development`, `staging`, `production`, `test`. En `staging`/`production` se refuerzan CORS, URL de base de datos y secretos. |
| `DATABASE_URL` | Sí | — | Cadena de conexión; ausente detiene la obtención de sesión y el arranque validado con error explícito. Fuera de `development`/`test` debe ser PostgreSQL. |
| `JWT_SECRET_KEY` | Sí | — | Clave de firma JWT; exige al menos 32 caracteres y rechaza valores de plantilla en el arranque validado. |
| `JWT_ALGORITHM` | No | `HS256` | Algoritmo de firma; el arranque validado rechaza valores distintos de `HS256`. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Vigencia del token de acceso en minutos. |
| `CORS_ORIGINS` | No / sí en `staging`/`production` | vacío | Lista separada por comas; activa CORS con GET/POST/PATCH y cabeceras `Authorization`/`Content-Type`, sin credenciales. En `staging`/`production` exige HTTPS y rechaza `*`. |
| `LOGIN_MAX_FAILURES` | No | `5` | Máximo de intentos fallidos de inicio de sesión por ventana; el arranque validado exige un entero positivo. |
| `LOGIN_WINDOW_SECONDS` | No | `900` | Ventana del límite de tasa en segundos; el arranque validado exige un entero positivo. |
| `TRUST_PROXY_HEADERS` | No | `false` | Activar sólo detrás de un proxy confiable que sobrescriba `X-Forwarded-For`. |
| `LOG_LEVEL` | No | `INFO` | Nivel mínimo de logs JSON (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`); valores inválidos se rechazan en la validación de entorno. |
| `GITHUB_TOKEN` | No / sí en `staging`/`production` | — | Token para el adaptador de GitHub; se rechazan valores de plantilla. |
| `SEED_USER_EMAIL`, `SEED_USER_PASSWORD` | No | — | Deben definirse juntos; la contraseña no debe ser valor de plantilla en `staging`/`production`. |
| `SENTRY_DSN` | No | — | Si se define, debe usar HTTPS. |
| `PROMETHEUS_ENABLED` | No | `false` | Debe ser booleano cuando se define. |

## 3. Seguridad implementada

- **Hash de contraseñas**: Argon2id (`argon2-cffi`) con parámetros centralizados en `src/securecode/api/security.py`, alineados con recomendaciones OWASP y valores por defecto de la biblioteca. Cada hash usa sal aleatoria; el hasher se crea una sola vez porque no mantiene estado mutable por solicitud.
- **Tokens de sesión**: JWT firmado (`HS256` por defecto) con `sub`, `iat`, `exp` y `jti` único; expiración de 60 minutos por defecto. Cada inicio de sesión crea una fila en `user_sessions` con el mismo `jti`; las solicitudes autenticadas exigen que la sesión exista, no esté revocada y no haya expirado.
- **Revocación**: `POST /api/v1/auth/logout` revoca la sesión actual y `POST /api/v1/auth/logout-all` revoca todas las sesiones del usuario. Los cambios de contraseña, desactivación o rol revocan todas las sesiones del afectado.
- **Estrategia de cookies y CSRF**: la consola web usa `POST /api/v1/auth/session`, recibe la sesión en la cookie HttpOnly `securecode_session` y el token CSRF en `securecode_csrf`; todas las operaciones inseguras requieren `X-CSRF-Token` y `Origin` del mismo sitio. Los clientes API conservan `Authorization: Bearer` mediante `POST /api/v1/auth/token` y no están sujetos a CSRF. CORS se ejecuta sin credenciales y `Secure` se activa en staging/production o HTTPS.
- **Límite de tasa en inicio de sesión**: 5 intentos fallidos (configurable) por ventana de 900 segundos (configurable). Verificado con pruebas (`tests/api/test_login_rate_limit.py`).
- **Igualación de tiempo en credenciales inexistentes**: se calcula el hash Argon2id de un usuario ficticio en memoria para que las respuestas de usuario inexistente tarden igual que las de contraseña incorrecta, reduciendo la enumeración de cuentas por tiempo de respuesta.
- **Cabeceras de seguridad**: middleware dedicado (`SecurityHeadersMiddleware`) aplicado a todas las respuestas; verificado con `tests/api/test_security_headers.py`.
- **CORS restrictivo**: solo orígenes declarados; sin credenciales; métodos GET/POST/PATCH.
- **Sin caché de contenido sensible**: las páginas HTML (sitio público y `/app`) se sirven con `Cache-Control: no-store, max-age=0`.
- **Autorización server-side**: cada endpoint valida rol/propiedad (dependencias de sesión y rol). Un token válido de Analista recibe 403 en FinOps, suscripción y administración (verificado en producción).
- **Validación de contraseñas**: registro exige mínimo 12 caracteres y fortaleza comprobada; las contraseñas débiles se rechazan con 422.
- **No persistencia de contraseñas temporales**: la contraseña temporal generada se muestra una vez y no se guarda en texto plano ni en el navegador.
- **Almacenamiento local del navegador**: solo `securecode_user` y `color-scheme`; la sesión se transporta en cookies y ningún JWT se guarda en `localStorage`.

## 4. Roles y modelo de datos operacional

- Roles únicos: `platform_admin`, `organization_owner`, `analyst` (validado por tipo literal en el modelo de respuesta de sesión).
- Registro público crea organización + propietario; rechaza campos desconocidos (422), duplicados (409) e intentos de inyección de rol (422). Verificado con `tests/api/test_auth.py` y `tests/api/test_app.py`.
- El Propietario gestiona Analysts de su organización (alta, habilitación/deshabilitación, restablecimiento de contraseña) y autorizaciones de repositorio por Analyst, con validación de formato `owner/repo`.
- Límite de Analysts activos por plan: Pro 3, Premium 10.
- Prueba Enterprise (`enterprise-trial`): crea organización con límites técnicos de repositorios y evaluaciones definidos en la configuración de la prueba; modos declarados `trial_non_billable` y estados `not_started`/`active`/`expired`. La respuesta nunca presenta la prueba como plan pagado. Verificado con `tests/api/test_enterprise_trial_http.py` y `tests/unit/test_enterprise_trial.py`.

## 5. Datos no conectados (qué NO debe prometer la operación)

El sistema declara estructuralmente que estos orígenes no están integrados; la operación no debe reportarlos como medidos:

| Dato | Estado declarado | Dónde |
|---|---|---|
| Facturación | `not_connected`; gasto observado siempre nulo; suscripción `demo_non_billable`; prueba `trial_non_billable` | FinOps, suscripción, informe de gestión |
| Métricas de CI | `not_connected` — "Consulta GitHub Actions para resultados y cobertura vigentes" | `/api/v1/system/overview` |
| Rendimiento en vivo | `not_live`; p95 y throughput nulos; documentados como pruebas controladas | `/api/v1/system/overview` |
| Capacidad/FinOps de plataforma | `not_connected` | `/api/v1/system/overview` |

La observabilidad operacional de Fase 12 emite logs JSON y contadores agregados por proceso; esto no convierte en "conectadas" las secciones comerciales de `/api/v1/system/overview`, que conservan su estado `not_live` / `not_connected`. El detalle está en [06-observabilidad.md](06-observabilidad.md).

## 6. Procedimientos operacionales

### 6.1 Dar de alta una organización
1. Desde el sitio público, completar el registro (organización, usuario, contraseña + confirmación, mínimo 12 caracteres).
2. Verificar que la respuesta sea exitosa; 409 indica organización/usuario existente.

### 6.2 Crear un Analyst y entregar credenciales
1. Como Propietario, en "Mi Organización", crear la cuenta con contraseña temporal generada o definida.
2. Comunicar la contraseña temporal por canal seguro; se muestra una sola vez y no queda almacenada.
3. El Analyst debe iniciar sesión y cambiar su contraseña (la temporal de una sola vez deja de funcionar tras el cambio; una temporal ya usada/expirada responde 401 "Incorrect username or password" — verificado en producción).

### 6.3 Restablecer la contraseña de un Analyst
1. Como Propietario, abrir el modal de restablecimiento en "Mi Organización".
2. Elegir: temporal generada (se muestra una vez) o definida por el Propietario. Si no se envía contraseña, la actual se conserva.
3. Confirmar el efecto: las sesiones activas del Analyst quedan revocadas de inmediato; el nuevo acceso usa la nueva credencial.

### 6.4 Revocar acceso de un Analyst a un repositorio
1. Como Propietario, quitar la autorización del repositorio en "Mi Organización".
2. Efecto inmediato: la siguiente evaluación del Analyst sobre ese repositorio es rechazada (403).

### 6.5 Suspender o deshabilitar un Analyst
1. Como Propietario, deshabilitar la cuenta desde "Mi Organización" (gestión de miembros).
2. Verificar con el Analyst que el acceso queda rechazado en el siguiente intento de evaluación.

### 6.6 Generar evidencia operacional
- Informe de gestión (Propietario): vista "Informe de Gestión" del menú lateral, con descarga CSV e impresión/PDF vía navegador. Desplegada en producción en la revisión activa `securecode-00046-94s` (100 % del tráfico), con el bundle `20261118-management-report`.
- Exportación de historial (cualquier rol): CSV `securecode-audit-history-<FECHA>.csv`.
- Verificación pública de evidencia: compartir `/api/v1/verify/{evaluation_id}` con terceros.

### 6.7 Respaldos y continuidad
- Objetivos de referencia técnica publicados por el sistema: disponibilidad 99.5 %, RTO cómputo "< 15 minutos", RPO base de datos "< 24 horas" (`/api/v1/system/overview`). Son metas técnicas, no compromisos contractuales.
- Respaldo portable: `python scripts\backup_postgres.py create --allowed-database <base_de_pruebas> --output-dir backups`, con la URL de origen entregada solo por `BACKUP_SOURCE_DATABASE_URL`.
- Verificación de artifact: `python scripts\backup_postgres.py verify --backup <archivo>.backup --manifest <archivo>.backup.manifest.json`.
- Restauración aislada: `python scripts\restore_postgres.py --backup <archivo>.backup --manifest <archivo>.backup.manifest.json --confirm RESTORE_TO_ISOLATED_TEST_DATABASE`, con `RESTORE_TARGET_DATABASE_URL` desde el gestor de secretos. Crea una base `securecode_restore_*`; nunca sobrescribe una base existente.
- Verificación integral: `python scripts\verify_backup_restore.py --output-dir artifacts\backup-verification`, que siembra dos organizaciones sintéticas, respalda, restaura y compara head de Alembic, 17 tablas, huellas por tabla e integridad referencial.
- Supabase documenta respaldos diarios en planes pagados y PITR como add-on con RPO máximo de dos minutos; la cobertura contratada y su activación deben confirmarse en el panel del proveedor. No se ha creado ningún job programado en este repositorio.
- Procedimiento completo, matriz de incidentes y automatización propuesta: [05-respaldos-y-recuperacion.md](05-respaldos-y-recuperacion.md).

### 6.8 Validación de configuración e instalación limpia
1. Ejecutar `python scripts/validate_environment.py` con la configuración del entorno. El comando no imprime secretos y falla con errores accionables si faltan variables o son incompatibles.
2. Sobre una base PostgreSQL vacía, ejecutar `python scripts/validate_fresh_install.py --database-url "$DATABASE_URL"`.
3. Confirmar en la salida: `alembic_check=clean`, `alembic_head=d4e9f1a2b3c4`, 18 tablas, `audit_details_type=JSONB`, integridad referencial y unicidad multiempresa.
4. Repetir `alembic current` y `alembic check` después de cualquier cambio de modelos o migraciones.

### 6.9 Cerrar sesión y revocar sesiones
1. El botón "Cerrar sesión" llama a `POST /api/v1/auth/logout` con la cookie de sesión, el token CSRF y el `Origin` del mismo sitio; después elimina el estado local del navegador.
2. Solo la sesión autenticada deja de ser válida de inmediato; un token copiado de esa sesión recibe 401 aunque no haya expirado.
3. Para revocar todas las sesiones del propio usuario, usar `POST /api/v1/auth/logout-all`.

## 7. Verificación de salud y diagnóstico

- Health check: `GET /health` responde `ok` (verificado en producción contra la revisión `securecode-00046-94s`). Como sondeo alternativo de la interfaz se puede usar `GET /app` (200 con `no-store`) o la OpenAPI de `/docs`.
- Liveness: `GET /health/live` responde `alive` sin consultar dependencias externas.
- Readiness: `GET /health/ready` valida configuración y PostgreSQL con timeout corto; responde `ready` o `503` con `reason` genérico (`configuration_invalid` o `database_unavailable`). No consulta GitHub.
- Correlación: todas las respuestas gestionadas devuelven `X-Request-ID`; el mismo valor aparece en los logs JSON de la solicitud. Un valor entrante inválido se sustituye por un identificador seguro.
- Diagnóstico de autenticación: errores de credenciales responden 401 con `{"detail": "Incorrect username or password"}`; bloqueo por límite de tasa tras exceder `LOGIN_MAX_FAILURES` dentro de `LOGIN_WINDOW_SECONDS`.
- Métricas internas: `GET /internal/observability/metrics` sólo admite `platform_admin` y muestra agregados de baja cardinalidad del proceso actual.
- Errores de validación de negocio responden 422 con mensajes en español (formato de repositorio, fortaleza de contraseña, límites de plan).

## 8. Pruebas y control de calidad operacional

- Suite local con PostgreSQL real: 378 pruebas aprobadas / 0 omitidas. La cifra vigente debe obtenerse ejecutando `pytest -q`; este registro corresponde a la validación del 2026-11-21.
- Suite sin PostgreSQL: 358 aprobadas / 20 omitidas.
- E2E de navegador: `python scripts/run_browser_session_e2e.py` valida login con cookie HttpOnly, CSRF, rechazo sin token/origen y logout con revocación.
- Análisis estático: `mypy` sin errores en 31 archivos fuente; Ruff sin hallazgos nuevos en los archivos de observabilidad (persisten 220 hallazgos preexistentes en `src`, `tests` y `scripts` fuera de Fase 12); JavaScript verificado con `node --check`; árbol sin conflictos de espacios (`git diff --check`).
- Pruebas de despliegue/configuración: `tests/unit/test_deploy002_config.py` y `tests/unit/test_environment_validation.py` cubren normalización de URL, seed y validación de arranque.

## 9. Registro de incidencias y deudas conocidas

| Ítem | Estado | Acción sugerida |
|---|---|---|
| 29 líneas con mojibake UTF-8 en `app.py` | Defecto cosmético preexistente, integrado y en producción | Corregir en una rama dedicada fuera de ES3 |
| Cambios sin confirmar en `main` (6 archivos) | Copias locales sin confirmar de funcionalidades ya desplegadas (páginas públicas + informe de gestión, revisión `securecode-00046-94s`) | Confirmar para mantener el árbol de trabajo limpio |
| Sufijos de bundle con fecha (`20261118-management-report`) | Convención vigente; la revisión de Cloud Run (`securecode-00046-94s`) es la referencia del despliegue | Documentar la convención de versionado |
| Canal comercial/privacidad sin configurar | Limitación declarada por el producto | Completar antes de cualquier uso comercial |
| Facturación no conectada | Estado estructural de la demo | Integrar proveedor de facturación antes de cobrar |
| Monitoreo externo y alertas no evidenciados en el repositorio | Pendiente de validación | Definir sondas y alertas sobre `/health` y `/app` |
