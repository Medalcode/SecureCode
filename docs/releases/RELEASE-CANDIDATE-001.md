# RELEASE CANDIDATE 001 — Preparación de release

**RELEASE VERSIONADO LOCALMENTE — NO PUBLICADO.**

## 1. Datos de preparación

- Fecha de preparación: 2026-11-21.
- Repositorio: `https://github.com/Medalcode/SecureCode`.
- Rama: `fix/console-logo-landing`.
- Commit base: `51beb05b84ccb4474bfeeddb423f9012d2f0e811`.
- Últimos commits base:
  - `51beb05 fix(ui): link console logo to public landing`
  - `e05fc8d Merge pull request #23 from Medalcode/fix/admin-legacy-role-listing`
  - `df786a6 fix(admin): normalize legacy role labels in user listing`
  - `dd0d9b6 Merge pull request #22 from Medalcode/feat/management-report-manuals`
  - `6130cc5 feat: add management reporting and delivery manuals`
- No se creó tag, push, PR ni despliegue.
- Se crearon seis commits locales de código más un commit documental final de manifiesto.

## 2. Estado del árbol de trabajo

- Modificados: 0.
- Sin seguimiento y candidatos: 0; los 106 candidatos originales quedaron versionados.
- Eliminados: 0.
- Conflictos: 0.
- Cambios en el índice: 0.
- Rama local adelantada respecto de `origin/fix/console-logo-landing`; no se ejecutaron `fetch`, `pull` ni `push`.
- No se ejecutaron `stash`, `reset`, `clean`, cambios de rama ni operaciones destructivas.
- Advertencias CRLF observadas en archivos de texto; no son errores de contenido.

## 3. Resumen ejecutivo

El árbol contiene un conjunto amplio y coherente de cambios de producto, pruebas, documentación e infraestructura declarativa. Los 106 candidatos originales quedaron versionados localmente, incluidas migraciones Alembic, módulos importados por la API, scripts operativos y documentos de cumplimiento.

No se encontraron secretos reales ni datos personales reales en los archivos candidatos legibles. Existe un archivo `.env` local ignorado con material de credencial local y credenciales de prueba en workflows; ninguno debe publicarse.

Las validaciones principales se reproducen: 378 pruebas con PostgreSQL, 358 aprobadas y 20 omitidas sin PostgreSQL, Alembic limpio en una base local vacía, mypy limpio y E2E de navegador correcto. Persisten 220 hallazgos Ruff preexistentes y el build Docker continúa bloqueado por falta de daemon.

Se corrigieron tres problemas menores de preparación de release: exclusiones insuficientes en `.gitignore`, exclusión de temporales en `.dockerignore`, exclusión del manifiesto operativo en `.gcloudignore` y ausencia del manifiesto de documentos en la imagen Docker. Estas correcciones están documentadas y verificadas estáticamente, pero el build de imagen no pudo ejecutarse.

## 4. Componentes incluidos

- Motor determinista GH-001, GH-002 y GH-003 y semántica PASS/FAIL/UNKNOWN.
- Backend y API FastAPI con health checks, observabilidad, sesiones revocables y CSRF.
- Modelos SQLAlchemy y cadena Alembic con un único head.
- Sitio público, páginas normativas y experiencia de consola.
- Reportes PDF y explicación de resultados.
- Documentación contractual versionada y manifiesto de integridad.
- Respaldos, restauración y verificación aislada PostgreSQL.
- Configuración de staging y plantilla Cloud Run declarativa.
- Pruebas unitarias, API, integración, benchmark y E2E de navegador.

## 5. Inventario por componente

Leyenda: `M` modificado, `??` sin seguimiento. Necesidad: `REQUIRED`, `SUPPORTING`, `OPTIONAL`, `NOT NEEDED`. Riesgo: `LOW`, `MED`, `HIGH`. Recomendación: `INCLUIR`, `EXCLUIR`, `REVISAR`.

| Ruta | Estado | Comp. | Función | Fase/evidencia | Necesidad | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| `.dockerignore` | M | I | Excluye temporales del build | Fase 14; este manifiesto | REQUIRED | LOW | INCLUIR |
| `.env.example` | M | I | Documenta APP_ENV, LOG_LEVEL y GITHUB_TOKEN | Fase 13; STAGE13-READINESS | REQUIRED | LOW | INCLUIR |
| `.gcloudignore` | M | I | Incluye manifiesto operativo en contexto | Fase 14; este manifiesto | REQUIRED | MED | INCLUIR |
| `.github/workflows/docker.yml` | M | J | Define APP_ENV=test para smoke | Fase 13; CI/test | REQUIRED | LOW | INCLUIR |
| `.github/workflows/gh001-e2e.yml` | M | J | Usa GITHUB_TOKEN con fallback | Fase 13; CI/E2E | REQUIRED | LOW | INCLUIR |
| `.github/workflows/postgresql-integration.yml` | M | J | Define APP_ENV=test en integración | Fase 13; CI/PostgreSQL | REQUIRED | LOW | INCLUIR |
| `.github/workflows/tests.yml` | M | J | Define APP_ENV=test en suite | Fase 13; CI/tests | REQUIRED | LOW | INCLUIR |
| `.gitignore` | M | I | Ignora temporales y credenciales locales | Fase 13/14 | REQUIRED | LOW | INCLUIR |
| `Dockerfile` | M | I | Copia manifiesto de documentos al runtime | Fase 14; este manifiesto | REQUIRED | HIGH | INCLUIR |
| `README.md` | M | L | Documenta sesiones, validación y respaldos | Fase 13; STAGE13-READINESS | SUPPORTING | LOW | INCLUIR |
| `alembic/versions/a9f3c1e7b205_user_sessions.py` | ?? | C | Crea tabla user_sessions | Fase 13; Alembic | REQUIRED | HIGH | INCLUIR |
| `alembic/versions/b7e4a2c9d615_single_membership_per_user.py` | ?? | C | Fuerza una membresía por usuario | Fase 13; Alembic | REQUIRED | HIGH | INCLUIR |
| `alembic/versions/c3f8a1d6e902_align_audit_json_type.py` | ?? | C | Alinea detalles a JSONB | Fase 13; Alembic | REQUIRED | HIGH | INCLUIR |
| `alembic/versions/d4e9f1a2b3c4_csrf_token_hash.py` | ?? | C | Añade csrf_token_hash | Fase 13; Alembic head | REQUIRED | HIGH | INCLUIR |
| `alembic/versions/f2b6c8d0a913_service_document_acceptances.py` | ?? | C | Crea aceptaciones documentales | Fase 13; Alembic | REQUIRED | HIGH | INCLUIR |
| `deploy/staging/cloud-run-service.yaml` | ?? | I | Plantilla Cloud Run staging | Fase 13; STAGING-001 | OPTIONAL | MED | INCLUIR |
| `docker-compose.yml` | M | I | Pasa variables de entorno | Fase 13; STAGE13-READINESS | REQUIRED | MED | INCLUIR |
| `docs/benchmark/gh001/results/gh001_benchmark_comparison.md` | ?? | L | Compara métricas v1 y v2 | Fase 13; v2 no adoptado | SUPPORTING | MED | REVISAR |
| `docs/benchmark/gh001/results/gh001_v1_metrics.json` | ?? | L | Métricas históricas v1 | Fase 13; v1 histórico | SUPPORTING | LOW | INCLUIR |
| `docs/benchmark/gh001/results/gh001_v2_proposed_metrics.json` | ?? | L | Métricas propuestas v2 | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `docs/benchmark/gh001/v1/gh001_benchmark_105_v1.snapshot.json` | ?? | L | Snapshot del dataset v1 | Fase 13; v1 histórico | SUPPORTING | LOW | INCLUIR |
| `docs/benchmark/gh001/v2/gh001_benchmark_105_v2.patch.json` | ?? | L | Parche propuesto del dataset | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json` | ?? | L | Dataset propuesto v2 | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json.sha256` | ?? | L | Huella del dataset propuesto | Fase 13; hash v2 | OPTIONAL | LOW | INCLUIR |
| `docs/benchmark/gh001/v2/gh001_v2_change_report.md` | ?? | L | Reporte de cambios v2 | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `docs/compliance/CONTROL-FICHES.md` | ?? | L | Fichas de control NIST | Fase 1; SCOPE-AND-EXCLUSIONS | SUPPORTING | LOW | INCLUIR |
| `docs/compliance/GH001_ORACLE_DISCREPANCY.md` | ?? | L | Documenta discrepancia del oráculo | Fase 7/13; v2 no adoptado | SUPPORTING | MED | REVISAR |
| `docs/compliance/NIST-800-53-TRACEABILITY.md` | ?? | L | Trazabilidad NIST parcial | Fase 1; SCOPE-AND-EXCLUSIONS | SUPPORTING | LOW | INCLUIR |
| `docs/compliance/SCOPE-AND-EXCLUSIONS.md` | ?? | L | Define alcance y exclusiones | Fase 1; SCOPE-AND-EXCLUSIONS | SUPPORTING | LOW | INCLUIR |
| `docs/compliance/SERVICE-ACCEPTANCE-ROLLBACK.md` | ?? | L | Procedimiento de rollback documental | Fase 7; integridad documental | SUPPORTING | LOW | INCLUIR |
| `docs/compliance/SERVICE_DOCUMENT_INTEGRITY.md` | ?? | L | Documenta integridad documental | Fase 7; SERVICE_DOCUMENT_INTEGRITY | SUPPORTING | LOW | INCLUIR |
| `docs/compliance/service_documents.manifest.json` | ?? | L | Manifiesto verificado de documentos | Fase 7; integridad documental | REQUIRED | HIGH | INCLUIR |
| `docs/manuals/01-manual-de-usuario.md` | M | L | Actualiza cookies y CSRF | Fase 13; manuales | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/02-manual-administracion-operacional.md` | M | L | Actualiza seguridad y respaldos | Fase 13; manuales | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/03-guia-demo.md` | M | L | Actualiza navegación con cookies | Fase 13; manuales | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/04-matriz-evidencia.md` | M | L | Actualiza evidencia de logout | Fase 13; manuales | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/05-respaldos-y-recuperacion.md` | ?? | L | Procedimiento de respaldo y recuperación | Fase 13; respaldos | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/06-observabilidad.md` | ?? | L | Manual de observabilidad | Fase 12; observabilidad | SUPPORTING | LOW | INCLUIR |
| `docs/manuals/README.md` | M | L | Indexa nuevos manuales e informes | Fase 13/14 | SUPPORTING | LOW | INCLUIR |
| `docs/releases/RELEASE-CANDIDATE-001.md` | ?? | L | Manifiesto de release candidato | Fase 14; este documento | REQUIRED | LOW | INCLUIR |
| `docs/specs/DEPLOY-003.md` | M | L | Actualiza revocación de sesión | Fase 13; deploy | SUPPORTING | LOW | INCLUIR |
| `docs/specs/EVALUATION-SEMANTICS.md` | ?? | L | Define semántica FAIL sobre UNKNOWN | Fase 13; EVALUATION-SEMANTICS | SUPPORTING | MED | INCLUIR |
| `docs/specs/GH-001.md` | M | L | Actualiza benchmarks v1 y v2 | Fase 7/13; v2 no adoptado | SUPPORTING | MED | REVISAR |
| `docs/specs/ORG-001.md` | M | L | Define aceptación documental obligatoria | Fase 7; integridad documental | SUPPORTING | LOW | INCLUIR |
| `docs/specs/PUBLIC-001.md` | M | L | Añade enlace y aceptación | Fase 7; PUBLIC-001 | SUPPORTING | LOW | INCLUIR |
| `docs/specs/STAGE13-READINESS.md` | ?? | L | Informe de preparación staging | Fase 13; STAGE13-READINESS | SUPPORTING | MED | REVISAR |
| `docs/specs/STAGING-001.md` | ?? | L | Arquitectura staging propuesta | Fase 13; STAGING-001 | SUPPORTING | MED | INCLUIR |
| `pyproject.toml` | M | I | Añade dependencia playwright | Fase 13; E2E navegador | REQUIRED | MED | INCLUIR |
| `scripts/backup_postgres.py` | ?? | G | Crea y verifica respaldos | Fase 13; respaldos | REQUIRED | HIGH | INCLUIR |
| `scripts/build_gh001_v2_proposal.py` | ?? | D | Genera propuesta v2 no adoptada | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `scripts/postgres_backup_lib.py` | ?? | G | Biblioteca segura de respaldo | Fase 13; respaldos | REQUIRED | HIGH | INCLUIR |
| `scripts/restore_postgres.py` | ?? | G | Restaura en base aislada | Fase 13; restauración | REQUIRED | HIGH | INCLUIR |
| `scripts/run_browser_session_e2e.py` | ?? | K | E2E de cookies y CSRF | Fase 13; E2E navegador | SUPPORTING | LOW | INCLUIR |
| `scripts/run_full_e2e.py` | M | K | Alinea token de entorno | Fase 13; E2E no ejecutado | SUPPORTING | LOW | INCLUIR |
| `scripts/run_gh001_dataset_benchmark.py` | ?? | D | Ejecuta benchmark GH-001 | Fase 13; benchmarks | SUPPORTING | LOW | INCLUIR |
| `scripts/seed_backup_fixture.py` | ?? | G | Siembra datos sintéticos | Fase 13; verificación | SUPPORTING | MED | INCLUIR |
| `scripts/validate_environment.py` | ?? | I | Valida configuración de arranque | Fase 13; validación entorno | REQUIRED | MED | INCLUIR |
| `scripts/validate_fresh_install.py` | ?? | C | Valida migraciones desde cero | Fase 13; instalación limpia | REQUIRED | HIGH | INCLUIR |
| `scripts/verify_backup_restore.py` | ?? | G | Verifica respaldo y restauración | Fase 13; verificación | REQUIRED | HIGH | INCLUIR |
| `src/securecode/adapters/postgres/models.py` | M | C | Añade sesiones y aceptaciones | Fase 13; modelos | REQUIRED | HIGH | INCLUIR |
| `src/securecode/api/app.py` | M | A | Integra sesiones, CSRF y endpoints | Fase 13; app | REQUIRED | HIGH | INCLUIR |
| `src/securecode/api/dependencies.py` | M | B | Resuelve principal autenticado | Fase 13; sesión/CSRF | REQUIRED | HIGH | INCLUIR |
| `src/securecode/api/normative_transparency.py` | ?? | E | Contenido normativo público | Fase 1/13; PUBLIC-001 | REQUIRED | LOW | INCLUIR |
| `src/securecode/api/public_site.py` | M | E | Publica contenido normativo | Fase 13; PUBLIC-001 | REQUIRED | LOW | INCLUIR |
| `src/securecode/api/schemas.py` | M | A | Añade hash al historial | Fase 13; esquemas API | REQUIRED | LOW | INCLUIR |
| `src/securecode/api/security.py` | M | B | Añade jti y decodificación | Fase 13; jti | REQUIRED | HIGH | INCLUIR |
| `src/securecode/api/service_document_manifest.py` | ?? | B | Verifica hash del manifiesto | Fase 7; integridad documental | REQUIRED | HIGH | INCLUIR |
| `src/securecode/api/service_documents.py` | ?? | B | Genera paquete documental | Fase 7; integridad documental | REQUIRED | HIGH | INCLUIR |
| `src/securecode/application/evaluation_report.py` | ?? | F | Genera informe PDF | Fase 13; PDF report | REQUIRED | MED | INCLUIR |
| `src/securecode/application/gh001_benchmark.py` | ?? | D | Calcula métricas del benchmark | Fase 13; benchmarks | SUPPORTING | LOW | INCLUIR |
| `src/securecode/application/result_explanation.py` | ?? | A | Explica resultados evaluados | Fase 13; resultados explicables | REQUIRED | MED | INCLUIR |
| `src/securecode/config.py` | ?? | I | Valida entorno y secretos | Fase 13; STAGE13-READINESS | REQUIRED | MED | INCLUIR |
| `src/securecode/engine/evaluator.py` | M | D | Ajusta semántica FAIL sobre UNKNOWN | Fase 13; semántica | REQUIRED | MED | INCLUIR |
| `src/securecode/observability.py` | ?? | H | Logs JSON y métricas | Fase 12; observabilidad | REQUIRED | MED | INCLUIR |
| `src/securecode/static/css/app.css` | M | E | Estilos de explicación y PDF | Fase 13; consola | REQUIRED | LOW | INCLUIR |
| `src/securecode/static/index.html` | M | E | Añade panel de explicación | Fase 13; consola | REQUIRED | LOW | INCLUIR |
| `src/securecode/static/js/app.js` | M | E | Migra a cookies y CSRF | Fase 13; consola web | REQUIRED | HIGH | INCLUIR |
| `src/securecode/static/public/site.css` | M | E | Añade tema y secciones normativas | Fase 13; sitio público | REQUIRED | LOW | INCLUIR |
| `tests/api/test_admin_http.py` | M | K | Actualiza headers y aceptación | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_app.py` | M | K | Simula sesiones revocables | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_auth.py` | M | K | Valida tokens con sesión | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_enterprise_trial_http.py` | M | K | Actualiza token de sesión | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_explainable_results.py` | ?? | K | Prueba resultados explicables | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_frontend_routes.py` | M | K | Verifica CSRF y explicaciones | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_gh002_app.py` | M | K | Actualiza token de sesión | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_normative_transparency.py` | ?? | K | Prueba transparencia normativa | Fase 1/13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_observability.py` | ?? | K | Prueba logs y métricas | Fase 12; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_organization_roles_http.py` | M | K | Añade aceptación documental | Fase 7/13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_phase5_audit_regressions.py` | ?? | K | Regresiones de auditoría Fase 5 | Fase 5; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_service_document_acceptance.py` | ?? | K | Prueba aceptación documental | Fase 7; suite | SUPPORTING | LOW | INCLUIR |
| `tests/api/test_session_security.py` | ?? | K | Prueba sesiones y CSRF | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/conftest.py` | M | K | Emite tokens con jti | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/integration/test_backup_restore.py` | ?? | K | Integración de respaldo/restauración | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/integration/test_membership_uniqueness.py` | ?? | K | Prueba unicidad de membresía | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/integration/test_postgres_integration.py` | M | K | Actualiza token de sesión | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/integration/test_schema_drift.py` | ?? | K | Prueba deriva de esquema | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/integration/test_service_acceptance_migration.py` | ?? | K | Prueba migración de aceptaciones | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_backup_restore_security.py` | ?? | K | Prueba seguridad de respaldo | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_environment_validation.py` | ?? | K | Prueba validación de entorno | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_evaluation_report.py` | ?? | K | Prueba generación PDF | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_gh001_benchmark_proposal.py` | ?? | K | Prueba propuesta v2 no adoptada | Fase 13; v2 no adoptado | OPTIONAL | MED | REVISAR |
| `tests/unit/test_normative_documentation.py` | ?? | K | Prueba documentación normativa | Fase 1/13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_observability_backup_errors.py` | ?? | K | Prueba errores de observabilidad | Fase 12/13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_result_explanation.py` | ?? | K | Prueba explicación de resultados | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_rule_cache.py` | ?? | K | Prueba caché de reglas | Fase 13; suite | SUPPORTING | LOW | INCLUIR |
| `tests/unit/test_security.py` | M | K | Verifica jti único | Fase 13; suite | SUPPORTING | LOW | INCLUIR |

Totales por componente, incluyendo excluidos: A 3, B 4, C 7, D 4, E 6, F 1, G 5, H 1, I 10, J 4, K 30, L 31, M 12. Total: 118 entradas conocidas; 106 candidatas y 12 excluidas.

Totales por recomendación: INCLUIR 96, REVISAR 10, EXCLUIR 12.

## 6. Archivos excluidos

Estos elementos no deben publicarse. Los artefactos temporales ad-hoc quedaron ignorados por las exclusiones añadidas en Fase 14; no se eliminaron del disco.

| Ruta | Estado | Comp. | Función | Fase/evidencia | Necesidad | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| `.kiro-role-tests/` | ?? | M | Artefactos temporales de roles | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.kiro-test-results.txt` | ?? | M | Resultado temporal de pruebas | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-argon2-final/` | ?? | M | Directorio temporal Argon2 | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-argon2-policy/` | ?? | M | Directorio temporal de política Argon2 | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-logo-final/` | ?? | M | Directorio temporal de logo | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-video-candidate-ci-fix/` | ?? | M | Directorio temporal CI video | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-video-candidate-postgres-fixture/` | ?? | M | Directorio temporal fixture PostgreSQL | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `.test-video-candidate/` | ?? | M | Directorio temporal de video | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `final_test_results.txt` | ?? | M | Resultado temporal de pruebas | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `output.txt` | ?? | M | Salida temporal | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `pytest_output.txt` | ?? | M | Salida temporal de pytest | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |
| `pytest_result.txt` | ?? | M | Resultado temporal de pytest | Sin evidencia de fase | NOT NEEDED | LOW | EXCLUIR |

También deben permanecer fuera del release:

- `.env` local ignorado.
- Bases locales `securecode.db`, `local_demo.db` y bases temporales de PostgreSQL.
- `artifacts/`, respaldos `.backup`, manifiestos de respaldo y `backup-verification-*.json`.
- Cachés `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/`.
- Entornos virtuales `venv/`, `.venv/`, `.venv_sc/`, `.venv_securecode/`.
- Directorios `.test-run-*/` y `.test-tmp-*/`, algunos con permisos restringidos.
- Claves privadas, cuentas de servicio, credenciales y dumps si aparecieran en el futuro.

## 7. Auditoría de secretos y datos sensibles

No se imprimieron valores. No se encontraron secretos reales, tokens de GitHub, claves privadas, credenciales de Supabase o Google Cloud, ni datos personales reales en archivos candidatos legibles.

| Ruta | Tipo de problema | Severidad | Acción correctiva |
|---|---|---|---|
| `.env` | Archivo local ignorado con material de credencial local | MEDIO | Mantener ignorado, no publicar, rotar si algún valor fue reutilizado fuera de local |
| `.github/workflows/tests.yml` | Credencial de prueba embebida para CI | BAJO | Confirmar uso exclusivamente de prueba; mover a secretos si se conecta a servicios reales |
| `.github/workflows/postgresql-integration.yml` | Credencial de prueba embebida para CI | BAJO | Confirmar uso exclusivamente de prueba; usar secretos del workflow |
| `.github/workflows/gh001-e2e.yml` | Referencia a `GITHUB_TOKEN` y fallback de prueba | BAJO | Verificar permisos mínimos y rotación del secreto real en CI |
| `.github/workflows/docker.yml` | Configuración de smoke test | BAJO | Confirmar que no recibe secretos reales |
| `README.md`, `docs/specs/GH-001.md`, `docker-compose.yml`, `.env.example` | Marcadores de configuración y credenciales de ejemplo | INFORMATIVO | Mantener como plantillas; impedir sustitución con valores reales |
| `local_demo.db`, `securecode.db`, `artifacts/backup-verification/*` | Bases y respaldos locales ignorados con datos sintéticos | BAJO | No publicar; conservar solo como evidencia local restringida |
| Directorios `.test-run-*/`, `.test-tmp-*/` | Directorios temporales parcialmente ilegibles | MEDIO | Revisar permisos o eliminar en limpieza autorizada antes del release |

`.gitignore` ahora excluye `.env.*` con excepción de `.env.example`, temporales `.test-*/`, salidas ad-hoc, cachés, entornos virtuales, claves, credenciales y dumps. No se ignoran archivos necesarios para reproducir la aplicación.

## 8. Migraciones Alembic

- Cadena completa: 17 revisiones desde `baseline` hasta `d4e9f1a2b3c4`.
- Un único head: `d4e9f1a2b3c4`.
- No hay revisiones perdidas en la cadena local.
- Migraciones nuevas sin seguimiento: `f2b6c8d0a913`, `b7e4a2c9d615`, `c3f8a1d6e902`, `a9f3c1e7b205`, `d4e9f1a2b3c4`.
- Validación en PostgreSQL local vacío `securecode_stage14_fresh`: upgrade completo, `alembic_check=clean`, 18 tablas, 17 índices, 9 restricciones únicas, `audit_details` JSONB, integridad referencial y unicidad de tenencia aplicadas.
- Vista previa offline de rollback `d4e9f1a2b3c4:c3f8a1d6e902`: elimina `csrf_token_hash`, el índice de sesiones activas y la tabla `user_sessions`; no se ejecutó.
- Precaución: `b7e4a2c9d615` rechaza duplicados de membresía; requiere precheck en la base destino.
- Precaución: `c3f8a1d6e902` es específica de PostgreSQL; requiere respaldo previo en staging.

## 9. Dependencias y consistencia

- `src/securecode/api/app.py` importa módulos sin seguimiento: `config.py`, `observability.py`, `service_documents.py`, `service_document_manifest.py`, `evaluation_report.py`, `result_explanation.py`, `normative_transparency.py` y `gh001_benchmark.py`; todos deben incluirse en el mismo release.
- `service_document_manifest.py` espera `docs/compliance/service_documents.manifest.json` en `parents[3]/docs/compliance`; el manifiesto debe seguimiento y debe empaquetarse.
- `Dockerfile` ahora copia el manifiesto a `/app/docs/compliance/service_documents.manifest.json`; no se pudo construir la imagen por falta de daemon.
- `.gcloudignore` ahora permite el manifiesto operativo en el contexto de Cloud Build; no se validó con `gcloud`.
- Las rutas frontend, contratos API y endpoints de documentos están alineados según pruebas API y E2E.
- `.env.example` y `deploy/staging/cloud-run-service.yaml` requieren revisión de nombres canónicos antes de staging; no se agregaron valores reales.
- `pyproject.toml` declara `playwright` sólo como dependencia de prueba; `requirements.txt` cubre dependencias de runtime usadas por Docker.
- Existen importaciones indirectas de `pydantic` y `starlette` vía FastAPI; no se modificaron por ser deuda previa.

## 10. Reproducibilidad

- Docker Client `29.6.2`.
- Docker daemon no disponible: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running`.
- Build de imagen no validado; no se declarará reproducible.
- Python activo: `3.14.6`.
- La imagen Docker usa Python `3.11-slim`.
- Existe un intérprete Python 3.11 local pero sin dependencias instaladas, por lo que la suite se ejecutó con el entorno disponible.
- No se instalaron herramientas globales ni se modificó Windows.
- PostgreSQL aislado local usado en puerto `55434` con binarios de `C:\Program Files\PostgreSQL\17\bin`; no se usaron bases externas.

## 11. Pruebas realizadas

- `python scripts/validate_fresh_install.py --database-url ...`: correcto; `alembic_check=clean`, head `d4e9f1a2b3c4`, 18 tablas, 17 índices, 9 unique constraints, JSONB, integridad referencial y unicidad de tenencia.
- `python -m pytest -q` sin PostgreSQL: `358 passed, 20 skipped`.
- `python -m pytest -q` con PostgreSQL y `pg_dump`/`pg_restore` en PATH: `378 passed`.
- Primera ejecución con PostgreSQL sin esos binarios en PATH: `376 passed, 2 skipped`; causa identificada y corregida para la ejecución final.
- `python -m mypy src`: `Success: no issues found in 31 source files`.
- `python -m ruff check --output-format concise src tests scripts`: `Found 220 errors`, `125 fixable`; deuda preexistente, no corregida indiscriminadamente.
- Ruff enfocado en módulos nuevos y de soporte: `All checks passed!`; al incluir `src/securecode/api/app.py` y `src/securecode/api/security.py` aparecen 76 hallazgos de estilo/deuda previa, principalmente `B008` e `I001`.
- `git diff --check`: sin errores; sólo advertencias CRLF.
- `python scripts/run_browser_session_e2e.py`: OK; cookies HttpOnly, CSRF, logout y sin JWT en localStorage.
- `python scripts/verify_backup_restore.py`: `status=ok`; SHA-256 del respaldo verificado; 17 tablas y 18 FK verificadas; 2 organizaciones sintéticas; restore correcto.
- `python -c "from securecode.api.service_document_manifest import load_document_manifest; ..."`: manifiesto cargado, versión `1.0`, 2 documentos.
- No se ejecutó `scripts/run_full_e2e.py` contra GitHub porque requiere credencial real y acceso externo no autorizado.

## 12. Benchmark

- GH-001 v1: 91/105, accuracy `0.8666666666666667`; permanece como referencia histórica.
- GH-001 v2 propuesto: 105/105, accuracy `1.0`; estado `PROPOSED_NOT_ADOPTED`.
- No se modificaron datasets esperados ni reglas para mejorar métricas.
- GH-002 y GH-003 están cubiertos por la suite y no se alteraron.
- Semántica PASS/FAIL/UNKNOWN documentada en `docs/specs/EVALUATION-SEMANTICS.md`.
- Los artefactos v2 deben revisarse antes de publicación; no deben presentarse como benchmark oficial.

## 13. Verificación del remoto

- `origin`: `https://github.com/Medalcode/SecureCode.git`.
- Rama actual: `fix/console-logo-landing`.
- Estado local conocido: up to date con `origin/fix/console-logo-landing`.
- Existen ramas locales con branches remotos y algunas `ahead 1`; no se modificaron.
- No se ejecutaron `fetch`, `pull` ni `push`.
- No se consultaron PRs de GitHub por no existir autorización para acceso externo; no se sobrescribió trabajo remoto.

## 14. Matriz de riesgos

| ID | Severidad | Evidencia | Impacto | Acción | Estado |
|---|---|---|---|---|---|
| R-01 | ALTO | Migraciones y módulos requeridos están sin seguimiento | Un commit parcial produciría release incompleto | Incluir todas las rutas REQUIRED en los commits 2 y 3 | ABIERTO |
| R-02 | ALTO | Docker daemon no disponible | Build no reproducible; imagen no validada | Validar build en entorno con daemon antes de staging | ABIERTO |
| R-03 | ALTO | `Dockerfile` y `.gcloudignore` corregidos en Fase 14 pero sin build real | El manifiesto operativo podría faltar en imagen publicada | Verificar imagen construida y endpoint de documentos en staging | ABIERTO |
| R-04 | ALTO | Documentos contractuales en estado borrador/con revisión legal pendiente | Riesgo comercial y de cumplimiento | Obtener aprobación legal antes de publicación | ABIERTO |
| R-05 | ALTO | Staging cloud, secretos, IAM y alertas no creados | No hay validación de despliegue real | Crear sólo con autorización y usar secret manager | ABIERTO |
| R-06 | MEDIO | Ruff reporta 220 hallazgos preexistentes | Deuda técnica; ruido en CI | No corregir indiscriminadamente; priorizar módulos nuevos ya limpios | MITIGADO PARA STAGING |
| R-07 | MEDIO | Benchmark v2 propuesto con accuracy 1.0 | Riesgo de presentarlo como oficial | Mantener etiqueta `PROPOSED_NOT_ADOPTED` y aprobación formal | ABIERTO |
| R-08 | MEDIO | `.env.example` y plantilla Cloud Run con posible deriva de nombres | Configuración incompleta en staging | Revisar nombres canónicos antes de crear secretos | ABIERTO |
| R-09 | MEDIO | `.env` local y directorios temporales ilegibles | Posible fuga si se empaquetan | Exclusiones añadidas; revisar permisos y no publicar | MITIGADO |
| R-10 | MEDIO | Migración `b7e4a2c9d615` rechaza duplicados | Fallo de aplicación en base con datos previos | Precheck de membresías y respaldo antes de apply | ABIERTO |
| R-11 | BAJO | Advertencias CRLF en diff | Ruido de herramientas, no error funcional | Normalizar sólo si el equipo lo decide | ACEPTADO |
| R-12 | BAJO | Ramas locales `ahead 1` | Posible confusión al seleccionar base de PR | Confirmar rama base antes de PR | ABIERTO |
| R-13 | MEDIO | E2E real contra GitHub no ejecutado | Integración externa no verificada | Ejecutar con token autorizado en staging | ABIERTO |
| R-14 | MEDIO | `STAGE13-READINESS.md` y benchmark docs requieren revisión antes de publicación | Podrían contener lenguaje de estado no final | Revisar textos en el commit de documentación | ABIERTO |

No hay riesgos CRÍTICOS conocidos de secreto expuesto o pérdida de datos inminente en los candidatos legibles.

## 15. Checklist previo a commit

- Confirmar que no hay secretos en los archivos seleccionados.
- No usar `git add .`; utilizar rutas explícitas.
- Verificar `git diff --cached --check` después de cada `git add`.
- Verificar que cada commit incluya código, migraciones y pruebas relacionadas cuando aplique.
- No incluir `.env`, bases locales, backups, temporales ni resultados de prueba.
- Revisar que los artefactos v2 estén etiquetados como propuestos.
- Confirmar que el manifiesto de documentos y su código verificador estén en el mismo commit o en commits consecutivos.
- Ejecutar nuevamente la suite completa antes del primer commit.

## 16. Checklist previo a push

- Obtener aprobación técnica y legal.
- Verificar rama base y estado remoto con operaciones de solo lectura.
- Confirmar que no se reescribió historial ni se usarán fuerzas.
- Revisar que el PR no incluya archivos excluidos.
- Ejecutar CI completa, incluido build Docker.
- Confirmar rotación de cualquier credencial local reutilizada.
- No publicar versión definitiva ni tag sin autorización.

## 17. Checklist previo a staging

- Crear recursos cloud y secretos con autorización explícita.
- Verificar build de imagen y carga del manifiesto operativo.
- Aplicar Alembic a una base vacía de staging tras respaldo.
- Verificar health checks, observabilidad y alertas propuestas.
- Ejecutar E2E de navegador y, si se autoriza, E2E real de GitHub.
- Verificar rollback de aplicación y documental.
- Confirmar que el benchmark v2 no se presenta como oficial.

## 18. Procedimiento de rollback

- Si un commit local es incorrecto: revertir en orden inverso con `git revert <sha>`; no reescribir historial.
- Si una migración ya se aplicó en staging: no ejecutar downgrade automático; restaurar desde respaldo verificado y seguir `docs/compliance/SERVICE-ACCEPTANCE-ROLLBACK.md`.
- Si el despliegue falla: redeploy de la imagen anterior y verificar `/health`, `/health/live` y `/health/ready`.
- Si la aceptación documental falla: conservar evidencia, bloquear publicación y repetir verificación de integridad del manifiesto.
- Nunca borrar datos de clientes ni bases externas como parte del rollback.

## 19. Plan de commits ejecutado

Se aplicó la alternativa B: varios commits por componentes. Un único commit de consolidación habría sido difícil de revisar con 106 rutas candidatas. Los comandos siguientes se ejecutaron con rutas explícitas, sin `git add .` ni `git add -A`.

### Commit 1 — Higiene y empaquetado de release

```powershell
git add -- .dockerignore .gitignore .gcloudignore Dockerfile docs/releases/RELEASE-CANDIDATE-001.md
```

### Commit 2 — Seguridad, sesiones, CSRF, observabilidad y esquema

```powershell
git add -- .env.example docker-compose.yml pyproject.toml alembic/versions/a9f3c1e7b205_user_sessions.py alembic/versions/b7e4a2c9d615_single_membership_per_user.py alembic/versions/c3f8a1d6e902_align_audit_json_type.py alembic/versions/d4e9f1a2b3c4_csrf_token_hash.py alembic/versions/f2b6c8d0a913_service_document_acceptances.py src/securecode/adapters/postgres/models.py src/securecode/api/app.py src/securecode/api/dependencies.py src/securecode/api/schemas.py src/securecode/api/security.py src/securecode/config.py src/securecode/observability.py tests/api/test_app.py tests/api/test_auth.py tests/api/test_frontend_routes.py tests/api/test_session_security.py tests/conftest.py tests/unit/test_security.py tests/unit/test_observability_backup_errors.py tests/unit/test_environment_validation.py tests/api/test_observability.py
```

### Commit 3 — Sitio público, cumplimiento, documentos y reportes

```powershell
git add -- src/securecode/api/public_site.py src/securecode/api/normative_transparency.py src/securecode/api/service_document_manifest.py src/securecode/api/service_documents.py src/securecode/application/evaluation_report.py src/securecode/application/result_explanation.py src/securecode/static/css/app.css src/securecode/static/index.html src/securecode/static/js/app.js src/securecode/static/public/site.css docs/compliance/CONTROL-FICHES.md docs/compliance/NIST-800-53-TRACEABILITY.md docs/compliance/SCOPE-AND-EXCLUSIONS.md docs/compliance/SERVICE-ACCEPTANCE-ROLLBACK.md docs/compliance/SERVICE_DOCUMENT_INTEGRITY.md docs/compliance/service_documents.manifest.json docs/specs/ORG-001.md docs/specs/PUBLIC-001.md docs/specs/EVALUATION-SEMANTICS.md tests/api/test_explainable_results.py tests/api/test_normative_transparency.py tests/api/test_service_document_acceptance.py tests/unit/test_evaluation_report.py tests/unit/test_normative_documentation.py tests/unit/test_result_explanation.py tests/unit/test_rule_cache.py
```

### Commit 4 — Motor y benchmarks GH

```powershell
git add -- src/securecode/engine/evaluator.py src/securecode/application/gh001_benchmark.py scripts/build_gh001_v2_proposal.py scripts/run_gh001_dataset_benchmark.py docs/specs/GH-001.md docs/compliance/GH001_ORACLE_DISCREPANCY.md docs/benchmark/gh001/results/gh001_benchmark_comparison.md docs/benchmark/gh001/results/gh001_v1_metrics.json docs/benchmark/gh001/results/gh001_v2_proposed_metrics.json docs/benchmark/gh001/v1/gh001_benchmark_105_v1.snapshot.json docs/benchmark/gh001/v2/gh001_benchmark_105_v2.patch.json docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json.sha256 docs/benchmark/gh001/v2/gh001_v2_change_report.md tests/unit/test_gh001_benchmark_proposal.py
```

### Commit 5 — Respaldos, restauración y scripts operativos

```powershell
git add -- scripts/backup_postgres.py scripts/postgres_backup_lib.py scripts/restore_postgres.py scripts/seed_backup_fixture.py scripts/validate_environment.py scripts/validate_fresh_install.py scripts/verify_backup_restore.py scripts/run_browser_session_e2e.py docs/manuals/05-respaldos-y-recuperacion.md docs/manuals/06-observabilidad.md tests/integration/test_backup_restore.py tests/unit/test_backup_restore_security.py
```

### Commit 6 — CI, documentación, staging y pruebas restantes

```powershell
git add -- .github/workflows/docker.yml .github/workflows/gh001-e2e.yml .github/workflows/postgresql-integration.yml .github/workflows/tests.yml README.md scripts/run_full_e2e.py docs/manuals/01-manual-de-usuario.md docs/manuals/02-manual-administracion-operacional.md docs/manuals/03-guia-demo.md docs/manuals/04-matriz-evidencia.md docs/manuals/README.md docs/specs/DEPLOY-003.md docs/specs/STAGE13-READINESS.md docs/specs/STAGING-001.md deploy/staging/cloud-run-service.yaml tests/api/test_admin_http.py tests/api/test_enterprise_trial_http.py tests/api/test_gh002_app.py tests/api/test_organization_roles_http.py tests/api/test_phase5_audit_regressions.py tests/integration/test_membership_uniqueness.py tests/integration/test_postgres_integration.py tests/integration/test_schema_drift.py tests/integration/test_service_acceptance_migration.py
```

### Registro de ejecución de commits

| Commit | SHA | Mensaje |
|---|---|---|
| 1 | `de7e9616bcd19a6422ce5372c47f35e5eebf5c57` | `chore(release): add packaging and release manifest guardrails` |
| 2 | `20206ec16dc9098739f1e5592e56e910001dcdbd` | `feat(api): harden sessions csrf and observability` |
| 3 | `28f9697fd05b076f7602b632c8697b646dd7ef5a` | `feat(compliance): publish public documents and reports` |
| 4 | `8f7d6d8e7d9e0465fe27aa86c756090d7024ab12` | `feat(evaluator): add gh001 benchmark evidence` |
| 5 | `bc3a363d18eda7d475663eb9f3369cd6ba10dab6` | `feat(ops): add backup restore and validation tooling` |
| 6 | `4e6dceeea5f5774e3a81b60504a432cae71e75a7` | `ci: complete staging docs and regression coverage` |
| 7 | Commit documental final | `docs(release): record local versioning evidence` |

- HEAD de código: `4e6dceeea5f5774e3a81b60504a432cae71e75a7`.
- Rango de commits de código: `51beb05..4e6dcee`.
- Cada commit se preparó con `git add -- <rutas explícitas>`, `git diff --cached --stat` y control de secretos sobre el diff staged; no se publicaron valores sensibles.
- El escaneo de alta confianza sobre `git diff 51beb05..HEAD` devolvió cero coincidencias para tokens GitHub, JWT, claves privadas, claves AWS y claves GCP.

## 20. Correcciones menores realizadas en Fase 14

- `.gitignore`: exclusiones adicionales para temporales, salidas ad-hoc, cachés, entornos virtuales, claves, credenciales y dumps; `.env.example` queda permitido.
- `.dockerignore`: exclusiones adicionales para temporales, cachés, salidas, reportes y artefactos sensibles.
- `.gcloudignore`: se preserva `docs/compliance/service_documents.manifest.json` en el contexto de Cloud Build.
- `Dockerfile`: se copia el manifiesto de documentos al runtime.
- Verificación: `git check-ignore` confirma que `.env`, temporales y salidas quedan ignorados, y que `.env.example` y el manifiesto operativo no quedan ignorados.
- No se modificaron reglas GH-001/002/003, contratos legales, benchmark externo ni datos de clientes.

## 21. Bloqueos

- Build Docker no validado por daemon no disponible.
- Staging cloud no creado; no se activaron secretos, IAM, service account, alertas ni presupuestos.
- Verificación real contra GitHub no ejecutada.
- Revisión legal pendiente.
- Artefactos benchmark v2 requieren aprobación formal.
- Configuración de environment de staging requiere revisión de nombres canónicos.
- Los 10 archivos marcados `REVISAR` requieren aprobación antes de publicación.

## 22. Validaciones finales posteriores a commits

- Estado Git final: árbol de trabajo limpio, índice limpio, 0 eliminados y 0 conflictos.
- `pytest -q` sin PostgreSQL: **358 passed, 20 skipped**.
- `pytest -q` con PostgreSQL aislado en `127.0.0.1:55434`: **378 passed**.
- `mypy src`: **Success: no issues found in 31 source files**.
- Ruff scoped de módulos nuevos y de soporte: **All checks passed!**
- Ruff global `src tests scripts`: **220 errores preexistentes**, deuda conocida documentada.
- Alembic: único head `d4e9f1a2b3c4`, historial lineal de 17 revisiones.
- Instalación limpia: migraciones aplicadas hasta `d4e9f1a2b3c4`, 18 tablas y `audit_details` como JSONB.
- Verificación de respaldo/restauración: `status=ok`, 2 organizaciones sintéticas, 17 tablas y 18 foreign keys verificadas; SHA del respaldo `4e781a94e33db6cd077eb830eb7df5f173d4839ba28074c382632def4bd0ca5d`.
- E2E de navegador: **OK**, con logout, CSRF y sin JWT expuesto en localStorage.
- `git diff --check 51beb05..HEAD`: sin errores, sólo advertencias CRLF.
- Escaneo de secretos: cero coincidencias de alta confianza en cada diff staged y en el rango completo `51beb05..HEAD`.
- No se ejecutaron `fetch`, `pull`, `push`, creación de PR, tags ni despliegues.

## 23. Estado de aprobación y veredicto

- Estado: **RELEASE VERSIONADO LOCALMENTE — NO PUBLICADO.**
- Veredicto: **APTO CON OBSERVACIONES** para preparar un pull request desde el historial local.
- No apto para push, PR remoto, tag, despliegue ni producción hasta completar los bloqueos anteriores.
- Los seis commits de código y el commit documental final existen sólo en la rama local.
