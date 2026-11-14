# P6 — Smoke test de control de acceso basado en roles

**Fecha:** 2026-11-14  
**Entorno:** producción, Cloud Run `securecode` en `us-central1`  
**URL:** `https://securecode-n43etfo4dq-uc.a.run.app`  
**Alcance:** comprobación de solo lectura. No se modificaron roles, usuarios, permisos ni evaluaciones.

## Objetivo

Confirmar que una visita sin sesión no puede consultar datos de auditoría ni usar funciones administrativas; además, comprobar que la interfaz no presenta el acceso de Administración ni un cierre de sesión inexistente antes de autenticar.

## Resultados sin credenciales

La siguiente comprobación HTTP se ejecutó contra producción sin encabezado `Authorization`:

| Ruta | Resultado esperado | Resultado observado |
| --- | --- | --- |
| `GET /api/v1/admin/users` | `401 Unauthorized` | `401` |
| `GET /api/v1/admin/user-audit-events` | `401 Unauthorized` | `401` |
| `GET /api/v1/admin/repository-authorizations` | `401 Unauthorized` | `401` |
| `GET /api/v1/evaluations/history` | `401 Unauthorized` | `401` |
| `GET /api/v1/system/overview` | `401 Unauthorized` | `401` |
| `GET /api/v1/auth/me` | `401 Unauthorized` | `401` |

La respuesta uniforme `401` confirma que el servidor no entrega historial, identidad ni recursos administrativos a una persona no autenticada. Esta es la barrera de seguridad determinante; ocultar elementos del navegador no se considera un control suficiente por sí solo.

## Interfaz inicial

El HTML entregado al visitante anónimo declara inicialmente:

```html
<button class="nav-item" data-view="admin" ... hidden aria-hidden="true">
<button type="button" class="btn-logout" id="btnLogout" hidden ...>
```

El cliente solo muestra la navegación de Administración cuando existe un token y el rol recibido es `admin`. Si alguien intenta navegar localmente a esa vista sin ese rol, el cliente vuelve al Evaluador de Controles. Los endpoints administrativos mantienen la autorización independiente en el servidor.

## Comprobación autenticada de rol auditor

Se utilizó una cuenta auditor aislada creada para esta verificación, con secreto efímero no conservado en el repositorio. La identidad autenticada obtuvo historial propio (`200`) y los cuatro recursos administrativos siguientes devolvieron `403 Forbidden`:

```text
GET /api/v1/admin/users                       403
GET /api/v1/admin/user-audit-events           403
GET /api/v1/admin/repository-authorizations   403
GET /api/v1/system/overview                   403
```

Esto diferencia correctamente ambos estados: sin token se rechaza con `401`; con un token válido de auditor se permite únicamente la funcionalidad propia y se rechaza administración con `403`.

## Controles de cuenta disponibles

La interfaz incluye `Cerrar sesión`, inicialmente oculto y visible únicamente para una sesión válida. La creación de cuentas está disponible en la consola administrativa y se protege por rol; no se expone como creación pública no autorizada.

## Riesgo residual y siguiente comprobación

El control server-side queda cubierto por este smoke test. Como evidencia adicional de presentación, debe realizarse una prueba manual en navegador con tres estados (visitante, auditor y administrador) antes de una demostración académica; no sustituye la autorización del servidor ya verificada.
