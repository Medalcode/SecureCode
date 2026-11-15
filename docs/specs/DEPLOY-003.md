# DEPLOY-003 — Hardening de aplicación y experiencia de operador

## Objetivo

Preparar SecureCode para un despliegue controlado, reduciendo exposición del navegador y evitando que la interfaz induzca prácticas inseguras de manejo de credenciales.

## Requisitos verificables

1. Toda respuesta HTTP de la aplicación debe incluir `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` y una CSP que impida ser embebida en marcos de terceros.
2. CORS debe aceptar exclusivamente orígenes explícitos en `CORS_ORIGINS`; no se permite `*` para la API autenticada.
3. La UI no debe persistir ni enviar tokens de GitHub desde el navegador. La integración SCM utiliza sólo el secreto configurado en el entorno de ejecución.
4. El usuario autenticado debe poder consultar una representación mínima de su identidad sin recibir hashes de contraseña, secretos o datos de otros usuarios.
5. La imagen de producción debe separar compilación y runtime, usar un usuario sin privilegios y no incluir herramientas de compilación en la capa final.
6. En Compose, la API debe ejecutarse sin capacidades Linux, sin escalamiento de privilegios y con filesystem de sólo lectura.
7. Las acciones de plataforma deben requerir `platform_admin`; las acciones de una empresa requieren `organization_owner`; un `analyst` sólo puede evaluar repositorios autorizados y consultar evidencia permitida de su propia organización.

## Criterios de aceptación

- `tests/api/test_security_headers.py` comprueba las cabeceras en `/health`.
- `tests/api/test_auth.py` comprueba que `/api/v1/auth/me` necesita JWT y no expone material de contraseña.
- La configuración de la interfaz explica que los secretos de GitHub son administrados por el servidor.
- La guía de despliegue contiene verificaciones de secretos, migración y revisión candidata antes de recibir tráfico.
- El esquema Alembic convierte los roles heredados a `platform_admin` y `analyst`, y agrega el rol `organization_owner` respaldado por membresías de organización. Las rutas `/api/v1/admin/*` rechazan usuarios sin `platform_admin`.
- El workflow manual `Candidate Deployment Smoke Test` valida una URL HTTPS candidata con secretos protegidos y conserva un artefacto no sensible.

## Límites actuales y siguiente incremento

El cierre de sesión elimina el token del navegador; la revocación inmediata de JWT requiere una lista de revocación compartida o sesiones de corta duración con refresh tokens. El rate limiting distribuido y WAF deben configurarse en el proveedor o gateway, no en memoria de una instancia de Cloud Run.
