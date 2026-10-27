# 🛡️ SecureCode UI: Memoria de Continuidad y Roadmap

> [!NOTE]
> **Identificador mnemotécnico en memoria:** `SECURECODE-FRONTEND-ROADMAP-2026`  
> **Fecha de última actualización:** 27 de Octubre, 2026  
> **Estado:** Fase 1 (Flujo L.E.R.) y Fase 2 Ítem 1 (Historial de Ejecuciones) 100% completados, probados y commiteados.

---

## 📌 1. Estado Actual Consolidado

Se implementaron las pantallas conforme a la **Sección 3.8 del Informe ES2 INACAP**, la paleta de **Stitch** y la persistencia real en **PostgreSQL**:

| Pantalla / Módulo | Rama Git | Endpoint Backend Conectado | Estado |
| :--- | :--- | :--- | :---: |
| **L — Login (`/login`)** | `features/frontend-login` | `POST /api/v1/auth/token` (Argon2id + JWT HS256) | ✅ 100% |
| **E — Evaluación (`/evaluacion`)** | `features/frontend-evaluacion` | `POST /api/v1/evaluations/gh-001` y `/gh-002` | ✅ 100% |
| **R — Resultado (`/resultado`)** | `features/frontend-resultado` | Recibe veredicto real persistido en PostgreSQL | ✅ 100% |
| **H — Historial (`/historial`)** | `features/frontend-historial` | `GET /api/v1/evaluations` (Filtros, búsqueda, paginación) | ✅ 100% |

### 🎨 Paleta Institucional Utilizada (Stitch):
* **Fondo de Pantalla**: `#F4F6FA` (Gris tenue limpio)
* **Contenedores y Tarjetas**: `#FFFFFF` (Blanco con radio de `8px`, borde `#E2E8F0` y sombra suave)
* **Azul Primario Institucional**: `#213F8B` (Títulos y botones principales)
* **Gris de Textos y Etiquetas**: `#555555`
* **Estados y Badges**:
  * 🟢 **PASS**: Fondo `#EBF7EE`, Borde `#C3E6CB`, Texto `#1E7E34` (`CONFORME`)
  * 🔴 **FAIL**: Fondo `#FDF2F2`, Borde `#F5C6CB`, Texto `#C0392B` (`NO CONFORME`)
  * 🟡 **UNKNOWN**: Fondo `#FFFBEB`, Borde `#FDE68A`, Texto `#B45309` (`DESCONOCIDO`)

### 🔑 Credenciales Locales Activas:
* **Usuario:** `auditor@empresa.com`
* **Contraseña:** `Password123!`
* **Base de datos:** PostgreSQL local en puerto `5432` (`securecode` con migraciones Alembic al día).
* **Backend:** FastAPI activo en `http://127.0.0.1:8000` con recarga activa.
* **Frontend:** Vite React activo en `http://localhost:5173`.

---

## 🌿 2. Estructura de Ramas en Git

```text
features/
  ├── frontend              (Rama base)
  ├── frontend-login        (Pantalla L)
  ├── frontend-evaluacion   (Pantalla E)
  ├── frontend-resultado    (Pantalla R)
  └── features/frontend-historial  (Pantalla H - Rama activa actual)
```

---

## 🚀 3. Roadmap Fase 2: Progreso y Próximos Pasos

### 1. Historial de Ejecuciones (Prioridad 1) — ✅ COMPLETADO
* **Frontend:** `HistorialView.jsx` con búsqueda por repo/hash, filtros por veredicto, tabla de 6 columnas, copiado de hash y modal de auditoría.
* **Backend:** `GET /api/v1/evaluations` en `app.py` y `list_evaluations` en `repository.py`.

### 2. Banco de Pruebas Unitario "de a 1" (Prioridad 2 — Gran Valor Académico)
* **Stitch:** Selector de casos Ground Truth (`GT-01`, `GT-02`, `GT-03`), previsualización de parámetros y botón "▶ Ejecutar Caso de Prueba" con métricas de tiempo y concordancia.
* **Base de Datos:** 🟢 Cero cambios (lee fixtures existentes).
* **Backend:**
  * Endpoint `GET /api/v1/test-bench/cases` (catálogo de escenarios).
  * Endpoint `POST /api/v1/test-bench/run` (ejecuta un escenario con el motor determinista y mide latencia en ms).

### 3. Centro de Control / Facturación (Billing) (Prioridad 3)
* **Stitch:** Tarjetas de "Plan Piloto Institucional ($150.000 CLP/mes)", "Consumo de Cuota de Evaluaciones (ej. 38/500)" e "Historial de Facturación".
* **Aclaración clave:** Refleja el modelo CANVAS y flujo de caja del Informe 1 (Sección 2.1.1.1 y 6.4.1).
* **Base de Datos:** 🟢 Consulta en vivo (`COUNT(*) WHERE evaluated_at >= inicio_mes`).
* **Backend:** Endpoint `GET /api/v1/billing/summary`.

### 4. Reporte PDF y Despacho por Correo (Prioridad 4)
* **Stitch:** Modal con previsualización del veredicto, hash firmado, campo de correo destinatario y botón "Generar PDF y Enviar".
* **Backend:** 
  * Endpoint `GET /api/v1/evaluations/{id}/pdf`.
  * Endpoint `POST /api/v1/evaluations/{id}/email`.
