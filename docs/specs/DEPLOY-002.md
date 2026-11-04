# DEPLOY-002: Hardening de Seguridad e Infraestructura para Despliegue en Producción

**Estado:** AUTORIZADO — Implementación en progreso  
**Protocolo:** SDD (Specification-Driven Development)  
**Rama:** `fix/deploy-002-security-config`  
**Referencia de Auditoría:** DEPLOY-002 Audit Report (2026-11-02)

---

## 1. Problema

La auditoría DEPLOY-002 identificó cuatro categorías de riesgo que bloquean un despliegue seguro en Google Cloud Run con Supabase PostgreSQL:

| # | Componente | Riesgo |
|---|---|---|
| 1 | `dependencies.py` | Sin `pool_pre_ping`; incompatible con conexiones TCP cerradas por inactividad en entornos serverless. Prefijo `postgres://` no normalizado. |
| 2 | `scripts/seed_user.py` | Credenciales predeterminadas hardcodeadas expuestas como fallback cuando no se proveen argumentos CLI. |
| 3 | `docker-compose.yml` | Credenciales de base de datos y clave JWT hardcodeadas en el archivo versionado. |
| 4 | `README.md` / `.env.example` | Guía de despliegue expone secretos en líneas de comando y omite la ejecución desacoplada de Alembic. |

---

## 2. Alcance Aprobado

### 2.1 `src/securecode/api/dependencies.py`
- Normalizar `postgres://` → `postgresql://` únicamente cuando el prefijo coincida.
- Añadir `pool_pre_ping=True` sólo cuando el dialecto es PostgreSQL.
- Añadir `pool_recycle=300` sólo cuando el dialecto es PostgreSQL (Cloud Run throttling).
- Preservar el comportamiento sin alteraciones para SQLite (tests).
- Prueba unitaria: configuración con URL PostgreSQL, con URL SQLite, con prefijo `postgres://`.

### 2.2 `scripts/seed_user.py`
- Eliminar las credenciales predeterminadas hardcodeadas del fallback.
- Leer el usuario de `SEED_USER_EMAIL` (variable de entorno) o primer argumento CLI posicional.
- Leer la contraseña de `SEED_USER_PASSWORD` (variable de entorno) o por `getpass.getpass()` interactivo.
- Fallar explícitamente si el usuario no se puede determinar.
- Prueba unitaria: sin credenciales, con variables de entorno, con getpass mockeado.

### 2.3 `docker-compose.yml`
- Reemplazar valores hardcodeados por referencias a variables de entorno con sintaxis `${VAR:?VAR must be set}` (Docker Compose validation obligatoria).
- Actualizar `.env.example` con las nuevas variables requeridas por Compose.

### 2.4 `README.md` y `.env.example`
- Sustituir ejemplo `--set-env-vars` con `--set-secrets` de Secret Manager.
- Documentar ejecución desacoplada de Alembic (Cloud Run Job o step de CI).
- Aclarar que rollback de aplicación (revisión Cloud Run) y rollback de BD (Alembic `downgrade`) son operaciones distintas e independientes.
- No incluir contraseñas ni tokens reales.

---

## 3. Restricciones

- GH-001, GH-002 y su motor de evaluación: sin modificación.
- Arquitectura hexagonal: sin cambios.
- No crear recursos externos (Supabase, Cloud Run, Secret Manager).
- No ejecutar despliegues.
- Sin merge directo a `main`; trabajo en `fix/deploy-002-security-config` y PR.
- No eliminar pruebas existentes.

---

## 4. Criterios de Aceptación

- [ ] Sin credenciales predeterminadas usables en `seed_user.py`.
- [ ] Compatibilidad SQLite preservada en suite de pruebas.
- [ ] `pool_pre_ping` activado exclusivamente para PostgreSQL.
- [ ] `docker-compose.yml` no contiene secretos; falla si variables no están definidas.
- [ ] Pruebas nuevas cubren lógica de configuración de conexión y seed.
- [ ] Suite completa 85+ passed, 0 failures.
- [ ] CI GitHub Actions verde en el PR.

---

## 5. Tareas

- [x] Crear rama `fix/deploy-002-security-config`.
- [x] Documentar DEPLOY-002.md.
- [ ] Modificar `src/securecode/api/dependencies.py`.
- [ ] Modificar `scripts/seed_user.py`.
- [ ] Modificar `docker-compose.yml`.
- [ ] Actualizar `README.md` y `.env.example`.
- [ ] Añadir `tests/unit/test_deploy002_config.py`.
- [ ] Ejecutar suite completa.
- [ ] Verificar que el diff no contiene credenciales reales.
- [ ] Abrir PR hacia `main`.
