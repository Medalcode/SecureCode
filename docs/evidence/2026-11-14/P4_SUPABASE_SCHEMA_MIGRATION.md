# P4 — Validación controlada de esquema Supabase

**Fecha:** 2026-11-14  
**Entorno:** Cloud Run `securecode`, proyecto GCP `securecode-513903`; PostgreSQL Supabase por pooler  
**Alcance:** migración Alembic de esquema; no se exportaron ni registraron credenciales.

## Objetivo

Confirmar que la base desplegada usa el secreto `securecode-db-url`, apunta a Supabase y alcanza el head requerido por Enterprise Trial.

## Evidencia previa

1. Cloud Run referencia `DATABASE_URL` desde Secret Manager (`securecode-db-url:latest`).
2. La inspección sanitizada del secreto confirmó PostgreSQL mediante `aws-1-us-east-1.pooler.supabase.com:6543`, base `postgres`; no se mostró usuario ni contraseña.
3. `python -m alembic current` devolvió `d5f4a1b9c302`.
4. `python -m alembic heads` devolvió `aa7c1e9d4f30 (head)`.

## Cambio autorizado y ejecutado

Con autorización explícita se ejecutó:

```text
python -m alembic upgrade head
```

Resultado observado:

```text
Running upgrade d5f4a1b9c302 -> aa7c1e9d4f30, add enterprise trial tenant quotas
```

La migración crea las tablas nuevas `organizations`, `organization_memberships`, `enterprise_trials`, `enterprise_trial_repositories` y `enterprise_trial_usages`, además de dos índices. No contiene borrados ni alteraciones de tablas existentes.

## Verificación posterior

```text
python -m alembic current
aa7c1e9d4f30 (head)
```

Una inspección de metadatos de PostgreSQL confirmó que están presentes las cinco tablas esperadas y que no falta ninguna.

## Límites y siguiente prueba

Esta evidencia confirma la migración de esquema, no el ciclo funcional completo de Enterprise Trial. El siguiente control debe crear y consultar un trial por API autenticada en el despliegue, sin consumir cupos de producción innecesariamente. El rollback requiere autorización independiente porque ejecutaría DDL de eliminación de tablas.
