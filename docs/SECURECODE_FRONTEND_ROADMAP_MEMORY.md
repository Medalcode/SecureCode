# 🛡️ SecureCode UI: Memoria de Continuidad y Roadmap

> [!NOTE]
> **Identificador mnemotécnico en memoria:** `SECURECODE-FRONTEND-ROADMAP-2026`  
> **Fecha de última actualización:** 27 de Octubre, 2026  
> **Estado:** Fase 1 (Flujo L.E.R.) y Fase 2 Ítems 1 y 3 (Historial y Billing) 100% completados, probados con pytest y commiteados.

---

## 📌 1. Estado Actual Consolidado

Se implementaron las pantallas conforme a la **Sección 3.8 del Informe ES2 INACAP**, la paleta de **Stitch** y la persistencia real en **PostgreSQL**:

| Pantalla / Módulo | Rama Git | Endpoint Backend Conectado | Estado |
| :--- | :--- | :--- | :---: |
| **L — Login (`/login`)** | `features/frontend-login` | `POST /api/v1/auth/token` (Argon2id + JWT HS256) | ✅ 100% |
| **E — Evaluación (`/evaluacion`)** | `features/frontend-evaluacion` | `POST /api/v1/evaluations/gh-001` y `/gh-002` | ✅ 100% |
| **R — Resultado (`/resultado`)** | `features/frontend-resultado` | Recibe veredicto real persistido en PostgreSQL | ✅ 100% |
| **H — Historial (`/historial`)** | `features/frontend-historial` | `GET /api/v1/evaluations` (Filtros, búsqueda, paginación) | ✅ 100% |
| **B — Facturación / Control (`/billing`)** | `features/frontend-billing` | `GET /api/v1/billing/summary` (Plan Piloto, cuotas, DTE) | ✅ 100% |

### 🎨 Paleta Institucional Utilizada (Stitch):
* **Fondo de Pantalla**: `#F4F6FA` (Gris tenue limpio)
* **Contenedores y Tarjetas**: `#FFFFFF` (Blanco con radio de `8px`, borde `#E2E8F0` y sombra suave)
* **Azul Primario Institucional**: `#213F8B` (Títulos y botones principales)
* **Gris de Textos y Etiquetas**: `#555555`
* **Estados y Badges**:
  * 🟢 **PASS / ACTIVO**: Fondo `#EBF7EE`, Borde `#C3E6CB`, Texto `#1E7E34`
  * 🔴 **FAIL**: Fondo `#FDF2F2`, Borde `#F5C6CB`, Texto `#C0392B`
  * 🟡 **UNKNOWN**: Fondo `#FFFBEB`, Borde `#FDE68A`, Texto `#B45309`

### 🔑 Credenciales Locales Activas:
* **Usuario:** `auditor@empresa.com`
* **Contraseña:** `Password123!`
* **Base de datos:** PostgreSQL local en puerto `5432` (`securecode`).
* **Lanzador Persistente:** Script `iniciar_servicios.bat` para levantar FastAPI y Vite en terminales Windows independientes sin desconexiones.

---

## 🌿 2. Estructura de Ramas en Git

```text
features/
  ├── frontend              (Rama base)
  ├── frontend-login        (Pantalla L)
  ├── frontend-evaluacion   (Pantalla E)
  ├── frontend-resultado    (Pantalla R)
  ├── frontend-historial    (Pantalla H)
  └── frontend-billing      (Pantalla B - Rama activa actual)
```

---

## 🚀 3. Roadmap Fase 2: Progreso y Próximos Pasos

### 1. Historial de Ejecuciones (Prioridad 1) — ✅ COMPLETADO
* **Frontend:** `HistorialView.jsx` con búsqueda por repo/hash, filtros, tabla de 6 columnas y modal de detalle.
* **Backend:** `GET /api/v1/evaluations` en `app.py`.

### 2. Banco de Pruebas Unitario "de a 1" (Prioridad 2 — Gran Valor Académico)
* **Stitch:** Selector de casos Ground Truth (`GT-01`, `GT-02`, `GT-03`), previsualización de parámetros y botón "▶ Ejecutar Caso de Prueba".
* **Backend:** Endpoint `GET /api/v1/test-bench/cases` y `POST /api/v1/test-bench/run`.

### 3. Centro de Control / Facturación (Billing) (Prioridad 3) — ✅ COMPLETADO
* **Frontend:** `BillingView.jsx` con tarjeta de suscripción "Plan Piloto Institucional ($150.000 CLP/mes)", barra de cuota de evaluaciones (38/500), cuota de almacenamiento cifrado (1.2 MB de 500 MB), tabla de facturación DTE con modal de comprobante y ejecutivo de asistencia corporativa.
* **Backend:** Endpoint `GET /api/v1/billing/summary` con consulta en vivo a PostgreSQL.

### 4. Reporte PDF y Despacho por Correo (Prioridad 4)
* **Stitch:** Modal con previsualización del veredicto, hash firmado, campo de correo y botón "Generar PDF y Enviar".
* **Backend:** Endpoints `GET /api/v1/evaluations/{id}/pdf` y `POST /api/v1/evaluations/{id}/email`.
