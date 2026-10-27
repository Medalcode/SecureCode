# 🛡️ SecureCode UI: Memoria de Continuidad y Roadmap

> [!NOTE]
> **Identificador mnemotécnico en memoria:** `SECURECODE-FRONTEND-ROADMAP-2026`  
> **Fecha de última actualización:** 27 de Octubre, 2026  
> **Estado:**  
> * **Fase 1 (Fórmula 3–4–2 Flujo L.E.R.):** 100% completada y validada.  
> * **Fase 2 - Pantalla 1 (Historial de Ejecuciones y Auditoría):** 100% completada y validada en PostgreSQL.  
> * **Fase 2 - Pantalla 2 (Centro de Control y Facturación Enterprise):** 100% completada y validada en vivo por el usuario.

---

## 📌 1. Estado Actual Consolidado de Pantallas

Todas las pantallas implementadas cumplen estrictamente con la **Sección 3.8 del Informe ES2 INACAP**, la paleta corporativa de **Stitch** y la persistencia de datos real en **PostgreSQL**:

| Pantalla / Módulo | Ruta Frontend | Rama Local Git | Endpoint Backend Conectado | Estado |
| :--- | :--- | :--- | :--- | :---: |
| **L — Login** | `/login` | `features/frontend-login` | `POST /api/v1/auth/token` (Argon2id + JWT HS256) | ✅ 100% |
| **E — Evaluación** | `/evaluacion` | `features/frontend-evaluacion` | `POST /api/v1/evaluations/gh-001` y `/gh-002` | ✅ 100% |
| **R — Resultado** | `/resultado` | `features/frontend-resultado` | Recibe y visualiza veredicto real persistido en PostgreSQL | ✅ 100% |
| **H — Historial** | `/historial` | `features/frontend-historial` | `GET /api/v1/evaluations` (Filtros, búsqueda, paginación, hash) | ✅ 100% |
| **B — Facturación** | `/billing` | `features/frontend-billing` | `GET /api/v1/billing/summary` (Plan Piloto, cuotas CI/CD, DTE) | ✅ 100% |

---

## 🎨 2. Paleta Institucional Utilizada (Stitch)
* **Fondo de Pantalla**: `#F4F6FA` (Gris tenue limpio)
* **Contenedores y Tarjetas**: `#FFFFFF` (Blanco con radio de `8px`, borde `#E2E8F0` y sombra suave)
* **Azul Primario Institucional**: `#213F8B` (Títulos, acentos y botones principales)
* **Gris de Textos y Etiquetas**: `#555555`
* **Estados y Badges**:
  * 🟢 **PASS / ACTIVO**: Fondo `#EBF7EE`, Borde `#C3E6CB`, Texto `#1E7E34` (`CONFORME` / `AL DÍA`)
  * 🔴 **FAIL**: Fondo `#FDF2F2`, Borde `#F5C6CB`, Texto `#C0392B` (`NO CONFORME`)
  * 🟡 **UNKNOWN**: Fondo `#FFFBEB`, Borde `#FDE68A`, Texto `#B45309` (`DESCONOCIDO`)

---

## 🔑 3. Credenciales y Entorno Local
* **Usuario de acceso:** `auditor@empresa.com`
* **Contraseña:** `Password123!`
* **Base de datos:** PostgreSQL local en puerto `5432` (`securecode` con migraciones Alembic al día).
* **Lanzador Persistente:** [`iniciar_servicios.bat`](file:///c:/Users/achej/Documents/SecureCode/iniciar_servicios.bat) para levantar FastAPI (8000) y Vite (5173) en terminales de Windows sin desconexiones.
* **Pruebas Automatizadas:** 4 pruebas unitarias de API aprobadas al 100% con `pytest` ([test_evaluations_history.py](file:///c:/Users/achej/Documents/SecureCode/tests/api/test_evaluations_history.py) y [test_billing.py](file:///c:/Users/achej/Documents/SecureCode/tests/api/test_billing.py)).

---

## 🌿 4. Estructura de Ramas en Git

```text
features/
  ├── frontend              (Rama base)
  ├── frontend-login        (Pantalla L - Login)
  ├── frontend-evaluacion   (Pantalla E - Evaluación GH-001/GH-002)
  ├── frontend-resultado    (Pantalla R - Resultado automático)
  ├── frontend-historial    (Pantalla H - Historial de Ejecuciones)
  └── frontend-billing      (Pantalla B - Centro de Control y Suscripción - Rama activa actual)
```

---

## 🚀 5. Roadmap Fase 2: Estado Detallado

### ✅ 1. Historial de Ejecuciones y Auditoría (COMPLETADO)
* **Frontend:** [`HistorialView.jsx`](file:///c:/Users/achej/Documents/SecureCode/frontend/src/views/HistorialView.jsx) con buscador en tiempo real por repositorio o hash, filtros tipo pill (`Todos`, `PASS`, `FAIL`, `UNKNOWN`), tabla de 6 columnas, copiado de hash SHA-256 al portapapeles y modal de auditoría detallado.
* **Backend:** Endpoint `GET /api/v1/evaluations` y método `list_evaluations` en `repository.py` sobre PostgreSQL.

### ✅ 2. Centro de Control y Facturación Enterprise (COMPLETADO)
* **Frontend:** [`BillingView.jsx`](file:///c:/Users/achej/Documents/SecureCode/frontend/src/views/BillingView.jsx) con:
  * Tarjeta de suscripción "Plan Piloto Institucional ($150.000 CLP/mes)".
  * RUT empresa (`76.842.109-K`) y modal de asistencia con ejecutivo corporativo asignado.
  * Consumo mensual de evaluaciones CI/CD (38 de 500) con barra de progreso.
  * Cuota de almacenamiento cifrado (1.2 MB de 500 MB) bajo retención de 365 días.
  * Historial de facturación tributaria (DTE) con modal de comprobante fiscal.
  * Footer institucional con SLA 99.9% y TLS 1.3.
* **Backend:** Endpoint `GET /api/v1/billing/summary` con métricas vivas calculadas desde PostgreSQL.

### ⏳ 3. Banco de Pruebas Unitario "de a 1" (Pendiente para arrancar)
* **Stitch:** Selector interactivo de casos Ground Truth (`GT-01`, `GT-02`, `GT-03`), previsualización de parámetros y botón "▶ Ejecutar Caso de Prueba" con métricas de tiempo de ejecución (ms) y concordancia.
* **Backend:** Endpoints `GET /api/v1/test-bench/cases` y `POST /api/v1/test-bench/run`.

### ⏳ 4. Reporte PDF y Despacho por Correo (Pendiente)
* **Stitch:** Modal con previsualización del veredicto, hash firmado, campo de correo destinatario y botón "Generar PDF y Enviar".
* **Backend:** Endpoints `GET /api/v1/evaluations/{id}/pdf` y `POST /api/v1/evaluations/{id}/email`.

---

## 💬 Frase de Reanudación para el Chat:
> *"Continuamos con SecureCode a partir de `SECURECODE-FRONTEND-ROADMAP-2026`. Flujo L.E.R., Historial y Facturación están 100% listos. Procedemos con la siguiente especificación del compañero."*
