# 🛡️ SecureCode UI: Memoria de Continuidad y Roadmap

> [!NOTE]
> **Identificador mnemotécnico en memoria:** `SECURECODE-FRONTEND-ROADMAP-2026`  
> **Fecha de última actualización:** 30 de Octubre, 2026  
> **Estado:**  
> * **Fase 1 (Fórmula 3–4–2 Flujo L.E.R.):** 100% completada y validada.  
> * **Fase 2 - Pantalla 1 (Historial de Ejecuciones y Auditoría):** 100% completada.  
> * **Fase 2 - Pantalla 2 (Centro de Control y Facturación Enterprise):** 100% completada.  
> * **Fase 2 - Pantalla 3 (Modal de Exportación PDF Estándar INACAP y Despacho):** 100% completada.  
> * **Fase 2 - Pantalla 4 (Banco de Pruebas Unitario "de a 1" Ground Truth):** 100% completada y validada.

---

## 📌 1. Estado Actual Consolidado de Pantallas

Todas las pantallas implementadas cumplen estrictamente con la **Sección 3.8 del Informe ES2 INACAP**, la paleta corporativa de **Stitch** y la persistencia de datos real en **PostgreSQL**:

| Pantalla / Módulo | Ruta Frontend | Rama Local Git | Endpoint Backend Conectado | Estado |
| :--- | :--- | :--- | :--- | :---: |
| **L — Login** | `/login` | `features/frontend-login` | `POST /api/v1/auth/token` (Argon2id + JWT HS256) | ✅ 100% |
| **E — Evaluación** | `/evaluacion` | `features/frontend-evaluacion` | `POST /api/v1/evaluations/gh-001` y `/gh-002` | ✅ 100% |
| **R — Resultado** | `/resultado` | `features/frontend-resultado` | Recibe veredicto real + Botón Exportar PDF | ✅ 100% |
| **H — Historial** | `/historial` | `features/frontend-historial` | `GET /api/v1/evaluations` + Botón Exportar PDF | ✅ 100% |
| **B — Facturación** | `/billing` | `features/frontend-billing` | `GET /api/v1/billing/summary` (Plan Piloto, cuotas, DTE) | ✅ 100% |
| **M — Modal Exportar PDF** | Modal Global | `features/frontend-export-pdf` | `POST /api/v1/evaluations/export` y `GET /pdf` | ✅ 100% |
| **T — Banco de Pruebas** | `/testbench` | `features/frontend-testbench` | `GET /cases` y `POST /run` (Oráculo GT-01 a GT-06) | ✅ 100% |

---

## 🎨 2. Paleta Institucional Utilizada (Stitch)
* **Fondo de Pantalla**: `#F4F6FA` (Gris tenue limpio)
* **Contenedores y Tarjetas**: `#FFFFFF` (Blanco con radio de `8px`, borde `#E2E8F0` y sombra suave)
* **Azul Primario Institucional**: `#213F8B` (Títulos, acentos y botones principales)
* **Gris de Textos y Etiquetas**: `#555555`
* **Estados y Badges**:
  * 🟢 **PASS / CONFORME / AL DÍA**: Fondo `#EBF7EE`, Borde `#C3E6CB`, Texto `#1E7E34`
  * 🔴 **FAIL / NO CONFORME**: Fondo `#FDF2F2`, Borde `#F5C6CB`, Texto `#C0392B`
  * 🟡 **UNKNOWN / DESCONOCIDO**: Fondo `#FFFBEB`, Borde `#FDE68A`, Texto `#B45309`

---

## 🔑 3. Credenciales y Entorno Local
* **Usuario de acceso:** `auditor@empresa.com`
* **Contraseña:** `Password123!`
* **Base de datos:** PostgreSQL local en puerto `5432` (`securecode` con migraciones Alembic al día).
* **Lanzador Persistente:** [`iniciar_servicios.bat`](file:///c:/Users/achej/Documents/SecureCode/iniciar_servicios.bat) para levantar FastAPI (8000) y Vite (5173).
* **Pruebas Automatizadas:** 14 pruebas unitarias de API aprobadas al 100% con `pytest`.

---

## 🌿 4. Estructura de Ramas en Git

```text
features/
  ├── frontend              (Rama base)
  ├── frontend-login        (Pantalla L - Login)
  ├── frontend-evaluacion   (Pantalla E - Evaluación GH-001/GH-002)
  ├── frontend-resultado    (Pantalla R - Resultado automático)
  ├── frontend-historial    (Pantalla H - Historial de Ejecuciones)
  ├── frontend-billing      (Pantalla B - Centro de Control y Suscripción)
  ├── frontend-export-pdf   (Modal M - Exportación PDF y Despacho)
  └── features/frontend-testbench (Pantalla T - Banco de Pruebas Unitario - Rama activa)
```

---

## 🚀 5. Roadmap Fase 2: Estado Detallado

### ✅ 1. Historial de Ejecuciones y Auditoría (COMPLETADO)
* `HistorialView.jsx` con búsqueda por repo/hash, filtros, tabla de 6 columnas y modal de detalle.
* Endpoint `GET /api/v1/evaluations` en `app.py`.

### ✅ 2. Centro de Control y Facturación Enterprise (COMPLETADO)
* `BillingView.jsx` con Plan Piloto ($150.000 CLP/mes), cuotas CI/CD (38/500), storage cifrado (1.2/500 MB), DTE fiscal y ejecutivo asignado.
* Endpoint `GET /api/v1/billing/summary` en vivo con PostgreSQL.

### ✅ 3. Exportar Reporte de Auditoría PDF y Despacho (COMPLETADO Y VERIFICADO)
* **Frontend:** [`ExportAuditModal.jsx`](file:///c:/Users/achej/Documents/SecureCode/frontend/src/components/ExportAuditModal.jsx) con:
  * Control evaluado, repositorio, veredicto con badge y hash SHA-256 canónico con botón de copiado.
  * Checkbox: *"Generar documento formal en formato PDF (Estándar INACAP)"* (checked por defecto).
  * Input: *"Enviar copia a correo del auditor"* (editable, por defecto `josemorahj23@gmail.com` / `auditor@empresa.com`).
  * Nota de seguridad: *"El reporte incluye la firma criptográfica y marcas de tiempo UTC para validez probatoria."*
  * Botones: *"Cancelar"* y *"Generar PDF y Enviar"*.
  * Descarga directa y automática del archivo `.pdf` en el navegador (`URL.createObjectURL(blob)`), sin dependencias externas.
  * Comprobante oficial de despacho en pantalla con Folio `DSP-YYYYMM-XXXXXX`, firma criptográfica SHA-256 y marca de tiempo UTC.
  * Facturación DTE ([`BillingView.jsx`](file:///c:/Users/achej/Documents/SecureCode/frontend/src/views/BillingView.jsx)): descarga directa de comprobantes fiscales electrónicos en PDF (`Factura_INV-2026-10-8841.pdf`) con resolución SII.
* **Backend:** 
  * Generador puro de PDF 1.4 conforme a estándar técnico INACAP ([`pdf_generator.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/application/pdf_generator.py)) y timbrado fiscal DTE.
  * Endpoint `POST /api/v1/evaluations/export` con persistencia de evidencia en `artifacts/dispatched_emails/{dispatch_id}.json`.
  * Endpoints `GET /api/v1/evaluations/pdf` y `GET /api/v1/billing/invoice-pdf` para descarga de archivos binarios con cabecera `Content-Disposition`.

### ✅ 4. Banco de Pruebas Unitario "de a 1" (COMPLETADO Y VERIFICADO)
* **Frontend:** [`TestBenchView.jsx`](file:///c:/Users/achej/Documents/SecureCode/frontend/src/views/TestBenchView.jsx) con:
  * Catálogo interactivo de 9 casos Ground Truth (GH-001 `GT-01` a `GT-06` y GH-002 `GT-01` a `GT-03`).
  * Selector por pestañas de control (`Todos`, `GH-001`, `GH-002`).
  * Vista detallada de evidencia de entrada (repositorio, rama, approvals, dismiss stale, default branch, protection enabled).
  * Modo edición/simulación para experimentar con parámetros personalizados en vivo.
  * Botón interactivo: **"▶ Ejecutar Prueba Unitario 'de a 1'"**.
  * Medición de latencia sub-milisegundo (1.2 ms, cumpliendo holgadamente el RNF $< 500$ ms).
  * Concordancia automática con oráculo (100% MATCH).
  * Hash canónico SHA-256 con copiado al portapapeles.
  * Panel de estadísticas de sesión (casos ejecutados, precisión, latencia promedio).
* **Backend:**
  * Motor determinista [`test_bench.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/application/test_bench.py).
  * Endpoints `GET /api/v1/test-bench/cases` y `POST /api/v1/test-bench/run`.
  * 6 pruebas unitarias específicas aprobadas en `tests/api/test_test_bench.py`.

---

## 💬 Frase de Reanudación para el Chat:
> *"Continuamos con SecureCode a partir de `SECURECODE-FRONTEND-ROADMAP-2026`. Tanto la Fase 1 como la totalidad de la Fase 2 (Historial, Facturación, Exportación PDF y Banco de Pruebas Unitario) están 100% completadas, probadas y verificadas."*
