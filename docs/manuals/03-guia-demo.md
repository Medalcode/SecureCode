# Guía de demostración — SecureCode (ES3)

Guion para la demostración presencial y el video de 12 a 15 minutos. Todos los pasos corresponden a funcionalidad verificada en el código o en auditorías de producción de esta entrega; los pasos condicionados al despliegue se marcan.

## 1. Contexto académico — campos a completar por el equipo

> Completar antes de entregar. Esta guía no inventa estos datos.

| Campo | Valor (completar) |
|---|---|
| Integrantes y roles en la demo | |
| RUT / código de estudiante | |
| Asignatura / curso y sección | |
| Profesor evaluador | |
| Fecha y hora de la demo presencial | |
| Enlace del video (YouTube/Drive) | |
| URL de la aplicación en producción | https://securecode-n43etfo4dq-uc.a.run.app |
| Consola (aplicación autenticada) | https://securecode-n43etfo4dq-uc.a.run.app/app |
| Repositorio del proyecto | (completar: repositorio GitHub del equipo) |

## 2. Preparación previa (checklist)

1. **Cuentas de demostración**: usar las cuentas de prueba autorizadas por el equipo (administradas por el encargado de credenciales; **no incluir contraseñas en esta guía, en el video ni en las láminas**). Cuentas disponibles para demo: propietario de la organización de demostración, analyst de la organización de demostración y administrador TI.
2. **Repositorios de referencia**: tener a mano un repositorio propio conforme (p. ej. `medalcode/securecode`, rama `main`) y, opcionalmente, un repositorio público no autorizado para mostrar el rechazo (en auditoría se usó `facebook/react`).
3. **Estado de producción**: el despliegue vigente (revisión `securecode-00046-94s`, 100 % del tráfico) incluye la vista "Informe de Gestión" (bundle `20261118-management-report`) y `/health` responde `ok`. Verificar `https://securecode-n43etfo4dq-uc.a.run.app/health` y el bundle al iniciar el ensayo.
4. **Conectividad**: verificar acceso a GitHub desde la instancia (la evidencia se consulta vía API de GitHub; sin `GITHUB_TOKEN` aplican límites no autenticados).
5. **Datos en pantalla**: decidir con antelación qué evaluaciones existentes se muestran (el historial y el informe exponen datos reales de la organización demo).
6. **Navegador**: usar un perfil limpio (la sesión vive en una cookie HttpOnly y el token CSRF se mantiene en memoria; cerrar sesión revoca la sesión en el servidor y elimina ambas cookies).

## 3. Guion cronometrado (12–15 minutos)

### Bloque 0 — Apertura y contexto (1 min)
- Mostrar la portada pública `/` y el mensaje central: "Plataforma para convertir políticas de repositorio en evidencia técnica verificable".
- Mencionar el alcance de la demo: controles GH-001, GH-002 y GH-003; evidencia con huella SHA-256; tres roles.

### Bloque 1 — Sitio público y transparencia (1–2 min)
- Recorrer `/nosotros` y `/preguntas-frecuentes` (qué evalúa, quién autoriza, qué ocurre con la evidencia, que no hay pagos reales).
- Abrir un documento informativo, p. ej. `/legal/sla` (encabezado "DOCUMENTO INFORMATIVO", fecha de última actualización) para mostrar que la oferta es académica y no comercial.
- En `/contacto`, destacar el aviso de no ingresar datos personales mientras el canal no esté configurado.

### Bloque 2 — Registro de organización (2 min)
- Registrar una organización nueva en vivo (nombre, usuario, contraseña + confirmación de mínimo 12 caracteres).
- Señalar los controles: contraseña débil rechazada (422), duplicado rechazado (409), y que la cuenta creada es propietaria de su organización.
- Iniciar sesión con la cuenta creada.

### Bloque 3 — Evaluador de controles (3 min)
- En "Evaluador de Controles", ejecutar **GH-002** sobre el repositorio conforme del equipo (en auditoría: `medalcode/securecode:main` → **PASS** con evidencia persistida).
- Explicar los tres estados con la lógica del motor: **PASS** (evidencia prueba cumplimiento), **FAIL** (evidencia prueba incumplimiento), **UNKNOWN** (evidencia insuficiente; lógica trivalente, un FAIL es concluyente aunque otra evidencia sea desconocida).
- Abrir la evaluación creada y mostrar el dictamen, los criterios contrastados y la huella SHA-256 de la evidencia.
- Copiar el identificador de evaluación y abrir `/api/v1/verify/{evaluation_id}` en otra pestaña: verificación pública de la evidencia.

### Bloque 4 — Organización y autorizaciones (3 min)
- Con la cuenta Propietario, en "Mi Organización":
  1. Crear un Analyst con contraseña temporal generada; mostrar el panel que entrega la temporal **una sola vez** y aclarar que no queda almacenada.
  2. Abrir el modal de restablecimiento (no se usan diálogos nativos del navegador): alternar entre contraseña temporal y definida; mostrar que un campo vacío conserva la contraseña actual.
  3. Autorizar al Analyst un repositorio (`owner/repo`) y mostrar el rechazo de un formato inválido ("El repositorio debe usar el formato owner/repo").
- Con la cuenta Analyst: iniciar sesión con la temporal, intentar evaluar un repositorio **no autorizado** y mostrar el 403 (en auditoría: `facebook/react` rechazado). Si se desea, evaluar el repositorio autorizado.

### Bloque 5 — Historial, exportación e informe (2–3 min)
- Mostrar el historial de evaluaciones y exportar el CSV (`securecode-audit-history-<FECHA>.csv`).
- Flujo del Informe de Gestión (desplegado en la revisión `securecode-00046-94s`, bundle `20261118-management-report`):
  1. **Iniciar sesión como Organization Owner** (la vista está oculta para otros roles).
  2. **Abrir "Informe de Gestión"** en el menú lateral.
  3. **Explicar los indicadores**: tarjetas (evaluaciones históricas, período actual, conformidad con desglose PASS/FAIL/UNKNOWN, cobertura autorizada, plan vigente) y tablas por control, por repositorio y de últimas 10 evaluaciones.
  4. **Descargar CSV** (`securecode-informe-gestion-<FECHA>.csv`).
  5. **Generar PDF** con "Imprimir / PDF", eligiendo "Guardar como PDF" en el diálogo del navegador.
- Subrayar el descargo del informe: el consumo y los cobros reales se muestran como no conectados; el informe solo reporta datos de la base de SecureCode.

### Bloque 6 — Consumo, plan/SLA y cierre (2 min)
- En "Consumo & FinOps": definir presupuesto y umbral de alerta; mostrar que la facturación está "SIN CONEXIÓN" y el cargo proyectado "No disponible".
- En "Plan & Niveles de Servicio (SLA)": mostrar el plan activo ("VIGENTE"), el catálogo Pro (150.025 CLP, 3 Analysts) / Premium (375.064 CLP, 10 Analysts) como proyecciones del informe ES2, el descargo de ausencia de pasarela de pago y el marco ITIL v4 (Warranty).
- Con la cuenta de Administrador TI (opcional): "Consola de Administración" y estado del sistema (CI `not_connected`, rendimiento `not_live`, SLA de referencia: 99.5 % disponibilidad, RTO "< 15 minutos", RPO "< 24 horas").
- **Cerrar sesión** y mostrar que el almacenamiento local queda limpio.

## 4. Preguntas probables del evaluador y respuestas verificables

| Pregunta | Respuesta con respaldo |
|---|---|
| ¿Qué pasa si la evidencia no es concluyente? | El motor devuelve `UNKNOWN` con lógica trivalente (código `src/securecode/engine/executor.py`); no se fuerza PASS ni FAIL. |
| ¿Cómo pruebo que la evidencia no fue alterada? | Cada evaluación guarda huella SHA-256 de la evidencia canónica; cualquier tercero la verifica en `/api/v1/verify/{evaluation_id}`. |
| ¿Se guardan las contraseñas temporales? | No: se muestran una vez al crear/restablecer y no se persisten (verificado también en `localStorage` de producción). |
| ¿Puedo cobrar por los planes? | No: no hay pasarela de pago; `demo_non_billable`/`trial_non_billable` y facturación `not_connected` son estados estructurales del sistema. |
| ¿Qué limita la cantidad de Analysts? | El plan: Pro 3, Premium 10; el exceso es rechazado por el servidor. |
| ¿Quién puede autorizar repositorios? | Solo el Propietario de la organización; el Analyst solo evalúa repositorios autorizados (403 en caso contrario, verificado en producción). |
| ¿Hay métricas de rendimiento reales? | El sistema las declara `not_live` y las documenta como pruebas controladas, no telemetría de producción. |

## 5. Riesgos y contingencias

| Riesgo | Contingencia |
|---|---|
| La revisión activa cambia entre el ensayo y la demo | Verificar antes de empezar `GET /health` (= `ok`) y que el HTML de `/app` contenga el bundle `20261118-management-report`; si la revisión cambió, repetir el ensayo del bloque 5. |
| GitHub limita las consultas (rate limit sin token) | Configurar `GITHUB_TOKEN` en la instancia o reutilizar una evaluación ya almacenada del historial. |
| Bloqueo por límite de tasa durante la demo (5 intentos fallidos/15 min) | Esperar la ventana o reiniciar el contador según configuración operacional; evitar probar contraseñas erróneas repetidamente. |
| Datos sensibles en pantalla | Usar la organización de demostración; no mostrar credenciales ni repositorios privados ajenos; cerrar sesión al final. |
| Caída de conectividad | Contar con las capturas del informe y del historial ya generadas por el equipo. **[pendiente de validación: el equipo debe preparar estas capturas]** |

## 6. Al terminar la demo

1. Cerrar sesión en todas las cuentas usadas.
2. Si se crearon organizaciones o Analysts de demostración en vivo, registrarlos para limpieza posterior (el Propietario puede deshabilitar cuentas desde "Mi Organización").
3. Dejar el enlace de verificación (`/api/v1/verify/{evaluation_id}`) de al menos una evaluación como comprobación abierta para el evaluador.
