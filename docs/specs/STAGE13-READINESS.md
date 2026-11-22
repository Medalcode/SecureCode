# SECURECODE — Fase 13: informe de preparación para staging

Fecha: 2026-11-21. Repositorio: `https://github.com/Medalcode/SecureCode`. Este informe documenta el estado observado en el árbol local en esa fecha y debe leerse como **histórico/local**. No implica despliegue, aprobación cloud ni preparación para producción.

## 1. Resumen ejecutivo

**Estado observado localmente (2026-11-21):** 378 pruebas aprobadas con PostgreSQL aislado, 358 aprobadas y 20 omitidas sin PostgreSQL, `mypy src` sin errores en 31 archivos fuente, migraciones desde cero hasta `d4e9f1a2b3c4`, `alembic check` limpio, E2E de navegador aprobado y respaldo/restauración verificado con datos sintéticos.

**Estado no verificado o pendiente:** build Docker en entorno con daemon disponible, entorno staging cloud creado, secretos/IAM/service account de staging, monitoreo/alertas activas, mediciones reales de costos, revisión jurídica contractual y smoke tests sobre despliegue real.

**Clasificación del documento:** evidencia histórica/local. **No usar como evidencia de despliegue cloud actual.**

**Veredicto histórico/local: APTO CON OBSERVACIONES PARA STAGING. NO APTO PARA PRODUCCIÓN.**

## 2. Estado de Git

**Histórico/local en 2026-11-21:**

- Rama: `fix/console-logo-landing`.
- HEAD observado: `51beb05b84ccb4474bfeeddb423f9012d2f0e811` (`51beb05 fix(ui): link console logo to public landing`).
- Archivos rastreados modificados: 40.
- Archivos no rastreados: varios cientos de artefactos de prueba, además de módulos fuente, migraciones, scripts, documentación y pruebas necesarios para el release.
- `git diff --stat`: 40 archivos, 1524 inserciones y 315 borrados.
- `git status` mostró advertencias `Permission denied` en directorios `.test-*` preexistentes; no se eliminaron ni modificaron.
- Una construcción desde ese HEAD habría sido incompleta: las migraciones posteriores a `c1a4d9e7f205`, `src/securecode/config.py`, `src/securecode/observability.py`, módulos de sesiones, PDF, cumplimiento y observabilidad estaban sin versionar.

**Estado posterior implementado en el repositorio local (no implica despliegue):** RC001 versionó el release candidate en commits locales hasta `255c3daa49ad9cd45977e94a96fefec655db06fb`. Esta sección se conserva como evidencia histórica de lo observado durante Fase 13.

### Archivos que debían incorporarse al siguiente release (histórico)

Rastreados modificados:

`.env.example`, `.github/workflows/docker.yml`, `.github/workflows/gh001-e2e.yml`, `.github/workflows/postgresql-integration.yml`, `.github/workflows/tests.yml`, `.gitignore`, `README.md`, `docker-compose.yml`, `docs/manuals/01-manual-de-usuario.md`, `docs/manuals/02-manual-administracion-operacional.md`, `docs/manuals/03-guia-demo.md`, `docs/manuals/04-matriz-evidencia.md`, `docs/manuals/README.md`, `docs/specs/DEPLOY-003.md`, `docs/specs/GH-001.md`, `docs/specs/ORG-001.md`, `docs/specs/PUBLIC-001.md`, `pyproject.toml`, `scripts/run_full_e2e.py`, `src/securecode/adapters/postgres/models.py`, `src/securecode/api/app.py`, `src/securecode/api/dependencies.py`, `src/securecode/api/public_site.py`, `src/securecode/api/schemas.py`, `src/securecode/api/security.py`, `src/securecode/engine/evaluator.py`, `src/securecode/static/css/app.css`, `src/securecode/static/index.html`, `src/securecode/static/js/app.js`, `src/securecode/static/public/site.css`, `tests/api/test_admin_http.py`, `tests/api/test_app.py`, `tests/api/test_auth.py`, `tests/api/test_enterprise_trial_http.py`, `tests/api/test_frontend_routes.py`, `tests/api/test_gh002_app.py`, `tests/api/test_organization_roles_http.py`, `tests/conftest.py`, `tests/integration/test_postgres_integration.py`, `tests/unit/test_security.py`.

No rastreados necesarios para el release:

- Migraciones: `alembic/versions/f2b6c8d0a913_service_document_acceptances.py`, `b7e4a2c9d615_single_membership_per_user.py`, `c3f8a1d6e902_align_audit_json_type.py`, `a9f3c1e7b205_user_sessions.py`, `d4e9f1a2b3c4_csrf_token_hash.py`.
- Código: `src/securecode/config.py`, `src/securecode/observability.py`, `src/securecode/api/normative_transparency.py`, `src/securecode/api/service_document_manifest.py`, `src/securecode/api/service_documents.py`, `src/securecode/application/evaluation_report.py`, `src/securecode/application/gh001_benchmark.py`, `src/securecode/application/result_explanation.py`.
- Scripts: `scripts/backup_postgres.py`, `scripts/postgres_backup_lib.py`, `scripts/restore_postgres.py`, `scripts/verify_backup_restore.py`, `scripts/seed_backup_fixture.py`, `scripts/validate_environment.py`, `scripts/validate_fresh_install.py`, `scripts/run_browser_session_e2e.py`, `scripts/build_gh001_v2_proposal.py`, `scripts/run_gh001_dataset_benchmark.py`.
- Documentación: `docs/manuals/05-respaldos-y-recuperacion.md`, `docs/manuals/06-observabilidad.md`, `docs/specs/EVALUATION-SEMANTICS.md`, todo `docs/compliance/`, todo `docs/benchmark/gh001/`.
- Pruebas: `tests/api/test_explainable_results.py`, `test_normative_transparency.py`, `test_observability.py`, `test_phase5_audit_regressions.py`, `test_service_document_acceptance.py`, `test_session_security.py`; `tests/integration/test_backup_restore.py`, `test_membership_uniqueness.py`, `test_schema_drift.py`, `test_service_acceptance_migration.py`; `tests/unit/test_backup_restore_security.py`, `test_environment_validation.py`, `test_evaluation_report.py`, `test_gh001_benchmark_proposal.py`, `test_normative_documentation.py`, `test_observability_backup_errors.py`, `test_result_explanation.py`, `test_rule_cache.py`.
- Nuevos de Fase 13: `docs/specs/STAGING-001.md`, `docs/specs/STAGE13-READINESS.md`, `deploy/staging/cloud-run-service.yaml`.

No deben incorporarse: `.kiro-role-tests/`, `.kiro-test-results.txt`, `.test-*/`, `final_test_results.txt`, `output.txt`, `pytest_output.txt`, `pytest_result.txt`.

## 3. Reproducibilidad del build

- Dockerfile usa `python:3.11-slim`, etapas builder/runtime, `PYTHONPATH=/app/src`, `PORT=8000`, `appuser` UID 10001, healthcheck `/health` y Uvicorn en `${PORT}`.
- `requirements.txt` coincide actualmente con dependencias de `pyproject.toml`, pero no hay lockfile ni constraints; las versiones son mínimos `>=`.
- `.dockerignore` excluye `.env`, `.env.*`, cachés y documentos, pero no excluye todos los directorios temporales `.venv*`/`.test-*`.
- No se encontraron secretos en la imagen por inspección estática; no se copia `.env`.
- Python activo por defecto es 3.14.6. Existe un intérprete 3.11.15 vía `py -V:Astral/CPython3.11.15`, pero no tiene las dependencias instaladas.
- Docker Client 29.6.2 está instalado, pero `docker version` falló con: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.

**Resultado: build NO VALIDADO por bloqueo exacto de daemon Docker.** Procedimiento queda documentado en `STAGING-001.md`. No se publicó imagen.

## 4. Arquitectura de staging propuesta

**Pendiente / no verificado en cloud.** Ver `docs/specs/STAGING-001.md` y `deploy/staging/cloud-run-service.yaml`. La propuesta describe servicio `securecode-staging`, base PostgreSQL exclusiva, secretos exclusivos, cuenta de servicio de mínimo privilegio, HTTPS administrado, CORS explícito, `APP_ENV=staging`, `maxScale=2`, `minScale=0`, CPU 1, memoria 512Mi, concurrencia 40 y probes `/health/live` y `/health/ready`. No se crearon recursos ni se verificó esta arquitectura en un entorno desplegado.

## 5. PostgreSQL y Alembic

- Cadena validada: 17 revisiones, una raíz, un head, sin duplicados.
- Head: `d4e9f1a2b3c4`; HEAD versionado por separado quedaría en `c1a4d9e7f205`.
- Base nueva aislada: `securecode_stage13_fresh`.
- `python scripts/validate_fresh_install.py --database-url ...` aplicó toda la cadena y devolvió `alembic_check: clean`, 18 tablas, 17 índices, 9 restricciones únicas, `details` JSONB, integridad referencial forzada y unicidad de tenencia forzada.
- `alembic history` y `alembic heads`: un solo head `d4e9f1a2b3c4`.
- No se usó SQLite como sustituto de pruebas PostgreSQL; las marcadas `postgres` se ejecutaron con DSN real.

## 6. Seguridad de autenticación

- Suite API y navegador cubre registro con aceptación documental, login Bearer y sesión, cookies HttpOnly/SameSite Lax, CSRF, logout, logout-all, revocación, expiración, bloqueo por intentos y desactivación de usuarios.
- `python scripts/run_browser_session_e2e.py` terminó con `E2E navegador OK`: sin JWT en localStorage, rechazo por CSRF faltante/origen incorrecto, logout y `/me` 401 posterior.
- `Secure` depende de HTTPS o entorno staging/production; no se comprobó en un servicio cloud real.
- No se desactivaron protecciones para probar.

## 7. Pruebas end-to-end

- 378 pruebas aprobadas con PostgreSQL aislado y `REQUIRE_POSTGRES_TESTS=1`.
- Verificación de respaldo creó datos sintéticos de dos organizaciones: 4 usuarios, 4 membresías, 6 evaluaciones, 6 evidencias, 4 aceptaciones y 2 sesiones; restauración conservó recuentos e integridad.
- Las evaluaciones con GitHub se cubren mediante adaptadores simulados y datasets; **no se ejecutó** `scripts/run_full_e2e.py` porque requiere token real de GitHub y consulta al repositorio externo ground-truth. No se afirma validación real de GitHub en esta fase.

## 8. Benchmarks

**Verificado localmente con artefactos del repositorio:**

- GH-001 v1 histórico: 105 casos, 91 coincidencias, 14 discrepancias, exactitud 0.8667.
- GH-001 v2 propuesto: 105 casos, 105 coincidencias, 0 discrepancias, exactitud 1.0.
- GH-001 v2 permanece `PROPOSED_NOT_ADOPTED`; no existe aprobación formal.
- GH-002 y GH-003: cubiertos por pruebas unitarias, API e integración dentro de la suite de 378 pruebas.
- Semántica confirmada: PASS=cumplimiento comprobado, FAIL=incumplimiento comprobado, UNKNOWN=evidencia insuficiente sin incumplimiento determinante. No se modificó el motor.

## 9. Observabilidad

- Logs JSON de una línea con `timestamp`, `level`, `event`, `service`, `environment`, `request_id` y campos permitidos; redacción de secretos.
- `X-Request-ID` validado y devuelto.
- Métricas HTTP y de evaluaciones por proceso en `/internal/observability/metrics`, protegido por `platform_admin`.
- `/health`, `/health/live` y `/health/ready` verificados.
- Error técnico de evaluación genera `evaluation.technical_error`; FAIL/UNKNOWN no se registran como ERROR.
- No se encontraron secretos en logs de las ejecuciones revisadas.
- Matriz de alertas preparada en `STAGING-001.md`; **no hay alertas Cloud Monitoring creadas**.

## 10. Respaldos y restauración

- `scripts/verify_backup_restore.py` terminó `status: ok`.
- SHA-256: `ff4c81e9b29101a9c28fefa1784df57cdc460126c740550d759bdc1570f8d952`.
- Respaldo: 42,656 bytes. Tiempos locales reales: 2,692 s backup y 0,833 s restore; duración total del verificado 3,8 s.
- Head Alembic conservado `d4e9f1a2b3c4`; 17 tablas verificadas y 18 foreign keys validadas.
- Conteos origen y restaurado idénticos para 17 tablas de datos.
- Estas medidas locales no son RPO/RTO garantizados en nube.

## 11. Rollback

- Aplicación: rollback de revisión Cloud Run es el mecanismo previsto. No se ejecutó.
- Worktree detached en `51beb05` importó la app anterior (48 rutas) y consultó una base con esquema actual `d4e9f1a2b3c4`: la reversión de aplicación es compatible con el esquema actual en esa comprobación local.
- Base: `alembic downgrade ... --sql` mostró que bajar desde `d4e9f1a2b3c4` elimina `csrf_token_hash` y la tabla `user_sessions`. No se ejecutó; rollback de esquema es potencialmente destructivo y requiere DBA.
- No se asume que rollback de Cloud Run revierte PostgreSQL.

## 12. Seguridad de infraestructura

Secretos, cuenta de servicio, HTTPS, HSTS e IAM de staging son propuestos o no verificados. CORS, CSP, cookies, validación de entorno y control administrativo están verificados en código o localmente. No se comprobó configuración cloud real; ver clasificación completa en `STAGING-001.md`.

## 13. Pipeline de release

Estrategia preparada con 14 pasos: Git, pruebas, migraciones, build, escaneo, candidato, migración controlada, smoke, seguridad, monitoreo, aprobación humana, tráfico progresivo y rollback. No se agregó workflow de despliegue automático a producción.

## 14. FinOps

Cloud Run con límites propuestos; PostgreSQL, Secret Manager, Logging, Monitoring y Artifact Registry propuestos o no disponibles; backup medido localmente. No se inventaron precios, consumo, presupuestos ni compromisos. Facturación de producto permanece `not_connected`.

## 15. Cumplimiento y contratación

La plataforma pública informa marco NIST SP 800-53 Rev. 5 como referencia, trazabilidad parcial, controles GH-001/002/003, semántica PASS/FAIL/UNKNOWN, alcance, exclusiones y limitaciones. No afirma certificación NIST. Los documentos legales siguen siendo borradores académicos con revisión jurídica pendiente; no se modificaron textos sustantivos.

## 16. Resultados pytest, mypy y Ruff

| Comando | Resultado |
|---|---|
| `python -m pytest -q` | 358 passed, 20 skipped |
| `python -m pytest -q` con PostgreSQL aislado y `REQUIRE_POSTGRES_TESTS=1` | 378 passed |
| `python scripts/validate_fresh_install.py ...` | head `d4e9f1a2b3c4`, `alembic check: clean` |
| `python scripts/run_browser_session_e2e.py` | OK |
| `python scripts/verify_backup_restore.py ...` | OK |
| Benchmarks GH-001 v1/v2 | ejecutados; v2 propuesto |
| `python -m mypy src` | Success: no issues found in 31 source files |
| `python -m ruff check src tests scripts` | 220 hallazgos preexistentes; 125 autocorregibles; sin hallazgos nuevos en archivos de Fase 12/13 |
| `git diff --check` | sin errores;Warnings CRLF preexistentes |

## 17. Hallazgos por severidad

| Severidad | Hallazgo | Estado | Impacto |
|---|---|---|---|
| ALTA | Código funcional no versionado al momento de Fase 13 | Histórico/local; mitigado por RC001 en commits locales | Un release desde HEAD de Fase 13 habría excluido migraciones y módulos críticos. |
| ALTA | Build Docker no validado por daemon caído | No verificado | No puede afirmarse build reproducible. |
| ALTA | Staging cloud no creado | Pendiente | No hay evidencia de comportamiento en Cloud Run, IAM, HTTPS ni red. |
| ALTA | Alertas cloud no activas | Pendiente | Solo existe matriz propuesta. |
| MEDIA | Ruff con 220 hallazgos preexistentes | Conocido | Deuda técnica; no bloquea funcionalidad local. |
| MEDIA | Entorno por defecto Python 3.14.6; 3.11.15 sin dependencias | Histórico/local | Riesgo de validar con intérprete distinto del contenedor. |
| MEDIA | Sin lockfile de dependencias | Pendiente | Build reproducible no garantizado a largo plazo. |
| MEDIA | HSTS y rate limiting distribuidos no verificados | Pendiente/no verificado | Requieren gateway/proveedor. |
| MEDIA | Revisión jurídica pendiente | Pendiente | No puede iniciarse contratación comercial real. |
| BAJA | Artefactos `.test-*`, logs y resultados sueltos sin versionar | Histórico/local | Ruido operativo; excluir del release. |

No se identificó un defecto funcional crítico en las pruebas ejecutadas en Fase 13.

## 18. Matriz de readiness

| Requisito | Estado | Evidencia | Riesgo | Acción pendiente | Responsable sugerido | Condición de aprobación |
|---|---|---|---|---|---|---|
| Código versionado | CONDICIONADA | Sección 2 | Release incompleto desde HEAD | Incorporar lista exacta | Tech Lead | Todo archivo de release presente en commit |
| Build reproducible | BLOQUEADA | Docker daemon caído; sin lockfile | No se puede construir | Iniciar Docker, build por digest, fijar dependencias | DevSecOps | Build limpio y digest registrado |
| Base PostgreSQL | VERIFICADA | Suite 378; base aislada | Ninguno local | Replicar en staging | DBA | Smoke staging |
| Migraciones | VERIFICADA | 17 revisiones; head único; check limpio | Rollback destructivo | Aplicar en staging con control | DBA | Migración staging aprobada |
| Autenticación | VERIFICADA | Suite API + browser E2E | Config cloud | Probar en staging | Backend/QA | Login staging OK |
| CSRF | VERIFICADA | Browser E2E sin token/origen inválido | Ninguno local | Repetir en staging | QA | Rechazos confirmados |
| Aislamiento multiempresa | VERIFICADA | Pruebas API/integración; 2 organizaciones sintéticas | Ninguno local | Repetir en staging | QA/Backend | Acceso cruzado denegado |
| Evaluaciones GH | VERIFICADA | 378 pruebas; benchmarks | GitHub real no ejecutado | Definir validación real autorizada | Backend | Resultados PASS/FAIL/UNKNOWN correctos |
| Evidencia e integridad | VERIFICADA | hashes y registros en suite/backup | Ninguno local | Verificar en staging | Backend/DBA | Hash consistente |
| Reportes PDF | VERIFICADA | pruebas unitarias/API | Ninguno local | Smoke PDF en staging | QA | PDF accesible solo a autorizado |
| Benchmark | VERIFICADA | v1 0.8667; v2 propuesto 1.0 | v2 no adoptado | Aprobación formal si se adopta | Producto/Gobernanza | Decisión documentada |
| Respaldos | VERIFICADA | SHA-256 y datos sintéticos | Automatización cloud ausente | Configurar scheduler autorizado | DBA/SRE | Respaldo staging verificado |
| Restauración | VERIFICADA | 17 tablas, 18 FK | RPO/RTO no medidos | Medir en nube | DBA | Restauración en nube documentada |
| Observabilidad | VERIFICADA local | logs JSON, request ID, health | Agregados por proceso | Configurar Cloud Logging | SRE | Logs centralizados |
| Alertas | PROPUESTA | matriz STAGING-001 | Sin detección automática | Crear alertas autorizadas | SRE | Alertas probadas |
| CI/CD | PARCIAL | workflows sin deploy automático | Build no probado | Pipeline completo con aprobación | DevSecOps | Ejecución end-to-end permitida |
| Rollback | PARCIAL | app compatible; DB no ejecutada | Pérdida de datos en downgrade | Runbook y prueba en staging | SRE/DBA | Reversión verificada |
| Secretos | PROPUESTA cloud | Secret Manager no creado | Uso de secretos productivos | Crear secretos staging | DevSecOps | Acceso restringido |
| Costos | NO MEDIDA | FinOps sección 14 | Gasto descontrolado | Definir límites y observación | FinOps/Producto | Presupuesto aprobado |
| Contratación y alcance | CONDICIONADA | documentos públicos y de cumplimiento | Revisión jurídica pendiente | Aprobación legal | Legal/Producto | Textos aprobados |

## 19. Acciones bloqueantes para producción

1. Versionar exactamente los archivos listados en la sección 2.
2. Validar build Docker con daemon funcional,fijar dependencias y publicar imagen por digest.
3. Crear staging cloud exclusivo con base, secretos, cuenta de servicio e IAM propios.
4. Aplicar migraciones en staging y ejecutar smoke tests HTTPS.
5. Activar y probar monitoreo/alertas.
6. Completar revisión de seguridad de infraestructura y aprobación humana.
7. Ensayar rollback de aplicación y plan de recuperación de base sin pérdida de datos.
8. Obtener revisión jurídica de documentos contractuales.
9. Realizar evaluación adicional con resultados reales del entorno desplegado.

## 20. Veredicto final

**APTO CON OBSERVACIONES PARA STAGING.** La funcionalidad, seguridad de aplicación, PostgreSQL, migraciones, autenticación, aislamiento, evidencias, PDF, observabilidad local y respaldo/restauración están validados en entornos locales aislados.

**NO APTO PARA PRODUCCIÓN.** La autorización definitiva requiere ejecución real en staging, build reproducible verificado, aprobación humana, alertas activas, revisión cloud y revisión jurídica. No se modificó producción ni se crearon recursos cloud.
