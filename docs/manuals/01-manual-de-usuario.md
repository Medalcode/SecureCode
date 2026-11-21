# Manual de usuario — SecureCode (ES3)

Manual de uso de la plataforma SecureCode. Todo lo descrito aquí proviene del código de la aplicación vigente en el árbol de trabajo al 2026-11-16 y del despliegue en producción (revisión `securecode-00046-94s`, bundle `20261118-management-report`); las limitaciones declaradas por el propio sistema (p. ej., facturación no conectada) se señalan expresamente.

## 1. Qué es SecureCode y a quién está dirigido

SecureCode convierte políticas de repositorio en evidencia técnica verificable: evalúa controles declarativos sobre la configuración observable de un repositorio y una rama (revisiones requeridas, protección de rama y firmas de commits), y conserva el dictamen, los criterios contrastados y una huella SHA-256 de la evidencia canónica para su verificación posterior.

El sistema reconoce exactamente tres roles:

| Rol | Identificador técnico | Alcance |
|---|---|---|
| Propietario de la organización | `organization_owner` | Administra su organización, sus cuentas Analyst, las autorizaciones de repositorios, la suscripción y el informe de gestión. |
| Analista | `analyst` | Ejecuta evaluaciones únicamente sobre los repositorios autorizados para su cuenta y consulta su historial. |
| Administrador TI | `platform_admin` | Consola de administración y estado del sistema. |

## 2. Sitio público

Disponible sin iniciar sesión en:

- `/` — portada: "Plataforma para convertir políticas de repositorio en evidencia técnica verificable".
- `/nosotros` — descripción del proyecto.
- `/contacto` — indica que el canal comercial definitivo aún no está configurado para este proyecto académico y advierte **no ingresar datos personales ni credenciales** mientras esos datos estén pendientes. Enlaza a la consola (`/app`).
- `/preguntas-frecuentes` — qué evalúa SecureCode, quién autoriza repositorios, qué ocurre con la evidencia, que no se procesan pagos reales y cómo se crean las cuentas.
- Documentos informativos bajo `/legal/{document}` (con encabezado "DOCUMENTO INFORMATIVO" y fecha de última actualización):
  - `/legal/terminos` — Términos de servicio.
  - `/legal/privacidad` — Política de privacidad.
  - `/legal/cookies` — Política de cookies (cookie de sesión HttpOnly, cookie CSRF y preferencias locales; sin analítica ni cookies de terceros).
  - `/legal/eula` — Acuerdo de licencia de usuario final.
  - `/legal/contratacion` — Condiciones de contratación y reembolsos (no procesa pagos).
  - `/legal/sla` — Acuerdo de nivel de servicio (indicadores de referencia técnica, no compromiso comercial).

Las páginas públicas se sirven con cabecera `Cache-Control: no-store` y un documento legal inexistente responde 404 ("Documento no encontrado").

## 3. Crear la organización e iniciar sesión

### 3.1 Registro de organización

El registro crea en un solo paso la organización y su cuenta propietaria:

- **Nombre de la organización**: entre 2 y 120 caracteres.
- **Usuario**: entre 3 y 100 caracteres.
- **Contraseña** y **confirmación de contraseña**: mínimo 12 caracteres. La plataforma valida la fortaleza; una contraseña débil es rechazada con error de validación (422).

Comportamientos relevantes (verificados con pruebas):

- Si la solicitud incluye campos no reconocidos, se rechaza con 422 (la API no ignora campos extra).
- Si la organización o el usuario ya existen, se responde 409 con mensaje en español.
- Intentos de inyectar un rol (`role`, `is_admin`, etc.) en el registro se rechazan con 422: la cuenta creada es siempre propietaria de su organización.

### 3.2 Inicio de sesión

- Formulario estándar de usuario y contraseña contra `/api/v1/auth/token`.
- Al autenticarse, la consola guarda en el almacenamiento local del navegador únicamente: `securecode_user` y la preferencia `color-scheme`. La sesión viaja en una cookie HttpOnly y el token CSRF se mantiene en memoria; **nunca se guardan contraseñas ni JWT en `localStorage`**.
- Tras 5 intentos fallidos (configurable) dentro de una ventana de 15 minutos (configurable), el acceso queda temporalmente bloqueado por límite de tasa.
- El cierre de sesión revoca la sesión en el servidor y elimina el estado autenticado y los datos de visualización asociados.

## 4. La consola (`/app`)

Al iniciar sesión se accede al shell de la aplicación con la siguiente navegación lateral (algunos ítems solo aparecen para roles con permiso):

| Vista | Título en la interfaz | Disponible para |
|---|---|---|
| Evaluador de controles | "Evaluador de Controles" | Todos los roles |
| Consumo | "Consumo & FinOps" | Propietario y Analista; el Administrador TI recibe 403 |
| Informe de gestión | "Informe de Gestión" | Solo Propietario (oculto para el resto) |
| Plan y niveles de servicio | "Plan & Niveles de Servicio (SLA)" | Propietario y Analista; el Administrador TI recibe 403 |
| Configuración | "Configuración del Cliente" | Todos los roles autenticados |
| Organización | "Mi Organización" | Solo Propietario (oculto para el resto) |
| Administración | "Consola de Administración" | Solo Administrador TI (oculto para el resto) |

El control de permisos se aplica en el cliente (ocultar/redirect) y **además en el servidor**: un Analista que invoque directamente los endpoints de FinOps, suscripción o administración recibe 403 (verificado en auditoría de producción).

## 5. Evaluador de controles

Vista principal para ejecutar evaluaciones de cumplimiento sobre un repositorio de GitHub.

### 5.1 Catálogo de controles

La interfaz consume `/api/v1/rules`, que publica únicamente el catálogo canónico usado por el motor (versión de catálogo `1`). Esto evita anunciar controles que no existen en el conjunto desplegado. El catálogo vigente:

- **GH-001 — Política de revisión de rama**: verifica que la rama evaluada exija revisiones.
- **GH-002 — Protección de rama por defecto**: verifica que la rama por defecto del repositorio esté protegida.
- **GH-003 — Exigencia de commits firmados**: verifica que la rama exija commits firmados.

### 5.2 Ejecutar una evaluación

1. Indicar el repositorio en formato `owner/repo` (por ejemplo, `medalcode/securecode`). Un formato inválido es rechazado con 422 y el mensaje "El repositorio debe usar el formato owner/repo".
2. Indicar la rama.
3. Elegir el control del catálogo y ejecutar.

Como Analista, solo puede evaluarse un repositorio **autorizado previamente** por el Propietario de su organización para su cuenta; un repositorio no autorizado es rechazado.

### 5.3 Resultados y significado de cada estado

- **PASS**: la evidencia obtenida prueba cumplimiento.
- **FAIL**: la evidencia obtenida prueba incumplimiento.
- **UNKNOWN**: no hay evidencia suficiente para probar ni cumplimiento ni incumplimiento (por ejemplo, un campo de evidencia ausente o no comparable). Es un estado deliberado del motor con lógica trivalente: en condiciones combinadas (AND), un FAIL es concluyente aunque otra parte de la evidencia sea desconocida.

Ejemplos verificados en producción: `GH-002` sobre `medalcode/securecode:main` arrojó **PASS** con evidencia persistida (huella SHA-256 `b1e1a72d…`), y la evaluación de un repositorio no autorizado (`facebook/react`) fue rechazada con 403.

### 5.4 Evidencia y verificación pública

Cada evaluación conserva el dictamen, los criterios contrastados y una huella SHA-256 de la evidencia canónica. Cualquier persona con el identificador de evaluación puede auditarla en el endpoint público `/api/v1/verify/{evaluation_id}`, que devuelve la verificación de la evidencia sin exponer la sesión del usuario. La interfaz permite consultar la evaluación individual (`/api/v1/evaluations/{evaluation_id}`) y el historial (`/api/v1/evaluations/history`).

### 5.5 Historial y exportación CSV

El historial de evaluaciones puede exportarse a CSV desde la interfaz; el archivo descargado se nombra `securecode-audit-history-<FECHA>.csv` (separador coma, codificación UTF-8).

## 6. Informe de Gestión (solo Propietario)

**Disponibilidad**: la vista está desplegada en producción en la revisión activa `securecode-00046-94s` (100 % del tráfico), con el bundle `20261118-management-report`. Es accesible únicamente para el rol `Organization Owner`, desde el ítem "Informe de Gestión" del menú lateral.

Genera un informe operativo de la organización a partir de datos reales de la base de SecureCode (nunca inventa datos de facturación, disponibilidad ni operación):

### Cómo generar el informe (paso a paso)

1. Iniciar sesión en `/app` con la cuenta **Organization Owner** de la organización.
2. Abrir el ítem **"Informe de Gestión"** en el menú lateral (oculto para los demás roles).
3. Revisar los indicadores: tarjetas resumen y tablas por control, por repositorio y de últimas evaluaciones.
4. Pulsar **"Descargar CSV"** para obtener el archivo `securecode-informe-gestion-<FECHA>.csv`.
5. Pulsar **"Imprimir / PDF"** y elegir "Guardar como PDF" en el diálogo de impresión del navegador.

### Contenido del informe

- **Tarjetas resumen**: Evaluaciones históricas, Período actual (mes calendario en curso, UTC), Conformidad (porcentaje PASS sobre dictámenes concluyentes PASS+FAIL, con desglose `PASS n · FAIL n · UNKNOWN n`; sin dictámenes muestra "—"), Cobertura autorizada (Analists activos y repositorios autorizados únicos) y Plan vigente.
- **Tablas**: Resultados por control, Resultados por repositorio y Últimas evaluaciones (hasta 10, con fecha, control, repositorio/rama, resultado y solicitante).
- **Acciones**: "Actualizar", "Descargar CSV" (archivo `securecode-informe-gestion-<FECHA>.csv`, separador `;` con BOM UTF-8) e "Imprimir / PDF" (usa el diálogo de impresión del navegador).
- **Declara su alcance**: el informe indica que el consumo de infraestructura y los cobros reales se muestran como no conectados mientras no exista integración con un proveedor de facturación (`billing_data_state: not_connected`, modo de suscripción `demo_non_billable`).

Los usuarios sin rol Propietario ven un aviso: "Inicia sesión como propietario de la organización para generar el informe de gestión" y, con sesión de otro rol, "Sólo el propietario de la organización puede generar este informe". El servidor aplica además 403 por defecto.

## 7. Consumo & FinOps

Vista de consumo con preferencias de presupuesto:

- **Presupuesto (CLP)** y **umbral de alerta (%)**: configurables; la alerta puede activarse o desactivarse.
- **Estado de facturación**: la insignia muestra "SIN CONEXIÓN" y el cargo proyectado "No disponible". El estado es estructural (`billing_data_state` es siempre `not_connected` y `observed_spend_clp` es siempre nulo): la plataforma registra evaluaciones y presupuesto, pero no gasto real.
- La API registra el alcance del dato (`account`, `organization` o `platform`), el período y el uso de evaluaciones del período y de toda la vida de la cuenta.

## 8. Plan & Niveles de Servicio (SLA)

- Encabezado de la vista: "Plan de Suscripción & Acuerdos de Servicio (SLA)" con compromisos operativos de garantía (Warranty) bajo el marco ITIL v4.
- **Plan activo**: nombre, insignia "VIGENTE", período (texto de vigencia) y lista de características del plan.
- **Estado comercial**: reglas de cambio de plan, con confirmación explícita (casilla de confirmación antes de aplicar el cambio; la acción es del Propietario).
- **Catálogo de planes vigente** (proyecciones comerciales del informe ES2, no cobrables):

| Plan | Precio (CLP) | Límite de Analysts | Características declaradas |
|---|---|---|---|
| Pro | 150.025 | 3 | 3 controles canónicos, hasta 3 Analyst, evidencia SHA-256, historial y exportación CSV |
| Premium | 375.064 | 10 | Todo lo incluido en Pro, hasta 10 Analyst, soporte prioritario según contrato |

- Cada plan declara además un límite técnico de repositorios y evaluaciones en su configuración.
- Aviso permanente: "Esta demostración no integra pasarela de pago ni genera cargos. Los montos son proyecciones comerciales del informe ES2."
- El sistema distingue el estado comercial del plan y los modos de uso no facturables: suscripción de demostración (`demo_non_billable`) y prueba técnica (`trial_non_billable`).

## 9. Configuración del cliente

Preferencias por usuario (persistidas vía `PATCH /api/v1/settings`):

- **Repositorio por defecto** (opcional) y **rama por defecto** para prellenar el evaluador.
- **Idioma**: `es-CL` o `en-US`.
- **Zona horaria**.
- **Tema**: `system` (según el sistema), `light` o `dark`.
- **Notificaciones**: evaluación completada, fallo de evaluación, resumen semanal (interruptores de preferencia de interfaz).

## 10. Mi Organización (solo Propietario)

Gestión del equipo y de los accesos:

### 10.1 Crear cuentas Analyst

- Formulario de alta con usuario y estrategia de contraseña:
  - **Generar temporal**: la plataforma genera una contraseña temporal fuerte (garantiza al menos un carácter de cada clase y la mezcla aleatoriamente) que se muestra **una sola vez** en un panel al crear la cuenta y **no queda almacenada**; el Propietario debe compartirla por un canal seguro y el Analyst debe cambiarla.
  - **Definir ahora**: el Propietario ingresa la contraseña definitiva; se aplica la misma política de fortaleza (mínimo 12 caracteres).
- Si el campo de contraseña se deja vacío, se interpreta como "generar temporal" (semántica acordada en ES3).
- El límite de Analysts activos proviene del plan (Pro: 3; Premium: 10); excederlo es rechazado.
- La creación es server-side autorizada: solo el Propietario de la organización puede crear cuentas en ella.

### 10.2 Restablecer contraseña de un Analyst

- Modal dedicado (no se usan diálogos nativos del navegador) con las dos estrategias: temporal generada o contraseña definida.
- Si no se indica una nueva contraseña, la cuenta conserva su contraseña actual.
- Al aplicar una temporal, el panel muestra la contraseña temporal una sola vez, con recordatorio de entrega segura.

### 10.3 Autorizar repositorios para un Analyst

- El Propietario define la lista de repositorios (`owner/repo`) que cada Analyst puede evaluar.
- Un repositorio con formato inválido es rechazado: "El repositorio debe usar el formato owner/repo".
- La revocación es inmediata: tras quitar la autorización, el Analyst pierde el acceso al repositorio (verificado en producción).
- También existen autorizaciones de repositorio a nivel de organización (endpoint de entitlements de Analyst), visibles para el Propietario.

## 11. Consola de Administración (solo Administrador TI)

- **Gestión de usuarios**: listado de cuentas del sistema (`/api/v1/admin/users`).
- **Estado del sistema** (`/api/v1/system/overview`): servicio "SecureCode Compliance Engine" versión 1.0.0, con los siguientes estados declarados:
  - Métricas de CI: `not_connected` — "Consulta GitHub Actions para resultados y cobertura vigentes".
  - Rendimiento: `not_live` — las métricas se documentan como pruebas controladas, no como telemetría de producción (p95 y throughput sin valor).
  - Capacidad/FinOps: `not_connected`.
  - **SLA de referencia técnica**: disponibilidad objetivo 99.5 %, RTO de cómputo "< 15 minutos", RPO de base de datos "< 24 horas". La vista de SLA pública aclara que estos indicadores no constituyen un compromiso comercial.

## 12. Buenas prácticas para el usuario

- No ingrese secretos, tokens ni información personal en los campos de repositorio (lo recuerda la política de privacidad).
- Comparta contraseñas temporales por un canal seguro y cámbielas en el primer inicio de sesión.
- Antes de tomar decisiones, revise el dictamen y los criterios contrastados de cada evaluación; use el estado `UNKNOWN` como señal de evidencia insuficiente, no como aprobación.
- Verifique la integridad de una evidencia cuando reciba su identificador, mediante el enlace público de verificación.
