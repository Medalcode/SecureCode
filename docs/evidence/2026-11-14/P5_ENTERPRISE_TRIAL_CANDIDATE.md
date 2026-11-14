# P5 — Prueba funcional Enterprise Trial en revisión candidata

**Fecha:** 2026-11-14  
**Candidata Cloud Run:** `securecode-enterprise-trial-fix`  
**Tráfico asignado:** 0 %  
**Imagen:** `sha256:a465af73daa6bd113c065f6585e62b5e50587f6fcddfbaeb45028bb1575f32b6`

## Incidencia detectada y corrección

La primera candidata reveló un `ForeignKeyViolation` de PostgreSQL al activar un trial: la aplicación añadía `organizations`, `organization_memberships` y `enterprise_trials` en un mismo flush sin una relación ORM que forzara el orden de inserción. SQLite sin claves foráneas activas no exponía el defecto.

La corrección `f7f7424` persiste y vacía primero la organización. La suite de Trial activa ahora `PRAGMA foreign_keys=ON` en SQLite para detectar esta clase de regresión. La validación local posterior fue:

```text
tests/unit/test_enterprise_trial.py: 5 passed
ruff: All checks passed
suite completa: 203 passed, 13 skipped
```

## Flujo candidato ejecutado

Se creó una cuenta auditor aislada, con una contraseña efímera no registrada en esta evidencia. En la URL etiquetada `candidate`, sin transferir tráfico, se comprobó:

1. Inicio de sesión JWT exitoso.
2. `GET /api/v1/enterprise-trial` devuelve `not_started`.
3. `POST /api/v1/enterprise-trial` con confirmación explícita devuelve `active` y `billing_mode: trial_non_billable`.
4. `POST /api/v1/enterprise-trial/repositories` autoriza `Medalcode/SecureCode`.
5. `POST /api/v1/evaluations/gh-002` con `Idempotency-Key` único devuelve `PASS` y `protection_enabled: true`.
6. Consulta final del trial confirma límites y consumo:

```json
{
  "repository_limit": 3,
  "repositories_used": 1,
  "evaluation_limit": 100,
  "evaluations_used": 1,
  "evaluation_control": "GH-002",
  "evaluation_status": "PASS"
}
```

No se creó facturación, cobro, renovación ni transferencia de tráfico. Los registros de prueba permanecen deliberadamente en Supabase como evidencia auditable; no contienen contraseñas en texto plano.

## Promoción y verificación posterior

El PR que contiene el fix fue fusionado como `552dd167aeac99a89f6e516a9ea0d6d56e29a6a4` tras aprobar `test` y `docker-smoke-test`. Con autorización separada, Cloud Run trasladó el 100 % del tráfico a `securecode-enterprise-trial-fix`.

Smoke test posterior en la URL principal:

```json
{
  "health_status": 200,
  "health_body": {"status": "ok"},
  "enterprise_trial_unauthenticated_status": 401
}
```

El `401` confirma que el endpoint está presente y protegido; un `404` habría indicado una imagen antigua. La revisión anterior no recibió tráfico tras la promoción.
