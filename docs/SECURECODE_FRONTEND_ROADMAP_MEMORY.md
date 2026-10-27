# 🛡️ SecureCode UI: Memoria de Continuidad y Roadmap

> [!NOTE]
> **Identificador mnemotécnico en memoria:** `SECURECODE-FRONTEND-ROADMAP-2026`  
> **Fecha de congelamiento:** 27 de Octubre, 2026  
> **Estado:** Fase 1 (Fórmula 3–4–2 Flujo L.E.R.) 100% completada y validada End-to-End. Preparado para Fase 2 (Nuevas funcionalidades del compañero).

---

## 📌 1. Estado Actual Consolidado (Fase 1: Flujo L.E.R.)

Se implementaron las **3 Pantallas Oficiales** conforme a la **Sección 3.8 del Informe ES2 INACAP** y la paleta exacta de **Stitch**:

| Pantalla | Rama Local Git | Endpoint Backend Conectado | Estado |
| :--- | :--- | :--- | :---: |
| **L — Login (`/login`)** | `features/frontend-login` | `POST /api/v1/auth/token` (Argon2id + JWT HS256) | ✅ 100% |
| **E — Evaluación (`/evaluacion`)** | `features/frontend-evaluacion` | `POST /api/v1/evaluations/gh-001` y `/gh-002` | ✅ 100% |
| **R — Resultado (`/resultado`)** | `features/frontend-resultado` | Recibe veredicto real persistido en PostgreSQL | ✅ 100% |

### 🎨 Paleta Institucional Utilizada (Stitch):
* **Fondo de Pantalla**: `#F4F6FA` (Gris tenue limpio)
* **Contenedores y Tarjetas**: `#FFFFFF` (Blanco con radio de `8px`, borde `#E2E8F0` y sombra suave)
* **Azul Primario Institucional**: `#213F8B` (Títulos y botones principales)
* **Gris de Textos y Etiquetas**: `#555555`
* **Estados y Badges**:
  * 🟢 **PASS**: Fondo `#EBF7EE`, Borde `#C3E6CB`, Texto `#1E7E34` (`CONFORME`)
  * 🔴 **FAIL / Error Form**: Fondo `#FDF2F2`, Borde `#D9534F` / `#F5C6CB`, Texto `#C0392B` (`NO CONFORME`)
  * 🟡 **UNKNOWN**: Fondo `#FFFBEB`, Borde `#FDE68A`, Texto `#B45309` (`DESCONOCIDO`)

### 🔑 Credenciales Locales Activas:
* **Usuario:** `auditor@empresa.com`
* **Contraseña:** `Password123!`
* **Base de datos:** PostgreSQL local en puerto `5432` (`securecode` con migraciones Alembic al día).
* **Backend:** FastAPI activo en `http://127.0.0.1:8000`.
* **Frontend:** Vite React activo en `http://localhost:5173`.

---

## 🌿 2. Estructura de Ramas en Git

Para evitar confusión en Git Extensions, todas las ramas quedaron agrupadas bajo la carpeta **`features/`**:

```text
features/
  ├── frontend              (Rama base)
  ├── frontend-login        (Pantalla L)
  ├── frontend-evaluacion   (Pantalla E)
  └── frontend-resultado    (Pantalla R - Rama activa actual)
```

> [!IMPORTANT]
> **Pendiente para Git Push a GitHub:**  
> Al intentar `git push`, GitHub arrojó `403 Forbidden` porque el repositorio pertenece a `Medalcode` y tu usuario es `josemorahj`.  
> **Solución:** Que `Medalcode` invite a `josemorahj` en `https://github.com/Medalcode/SecureCode/settings/access`.

---

## 🚀 3. Roadmap Fase 2: Las 4 Nuevas Funcionalidades del Compañero

Para cada una se redactó el **prompt de Stitch** y se identificaron los **tasks de Backend y Base de Datos**:

### 1. Historial de Ejecuciones (Prioridad 1 — Muy Alta Viabilidad)
* **Stitch:** Tabla limpia con `ID Evaluación`, `Fecha (UTC)`, `Control`, `Repositorio`, `Veredicto` (Badge) y `Hash`.
* **Base de Datos:** 🟢 Cero cambios (tabla `evaluation_records` ya almacena todo en PostgreSQL).
* **Backend:** 
  * Crear método `list_evaluations` en `repository.py`.
  * Endpoint `GET /api/v1/evaluations` en `app.py` (con paginación y filtro de estado).

### 2. Banco de Pruebas Unitario "de a 1" (Prioridad 2 — Gran Valor Académico)
* **Stitch:** Selector de casos Ground Truth (`GT-01`, `GT-02`, `GT-03`), previsualización de parámetros y botón "▶ Ejecutar Caso de Prueba" con métricas de tiempo y concordancia.
* **Base de Datos:** 🟢 Cero cambios (lee fixtures existentes).
* **Backend:**
  * Endpoint `GET /api/v1/test-bench/cases` (catálogo de escenarios).
  * Endpoint `POST /api/v1/test-bench/run` (ejecuta un escenario con el motor determinista y mide latencia en ms).

### 3. Centro de Control / Facturación (Billing) (Prioridad 3)
* **Stitch:** Tarjetas de "Plan Piloto Institucional ($150.000 CLP/mes)", "Consumo de Cuota de Evaluaciones (ej. 38/500)" e "Historial de Facturación".
* **Aclaración clave:** No es cobro real bancario; refleja el modelo CANVAS y flujo de caja del Informe 1 (Sección 2.1.1.1 y 6.4.1).
* **Base de Datos:** 🟢 Consulta en vivo (`COUNT(*) WHERE evaluated_at >= inicio_mes`).
* **Backend:** Endpoint `GET /api/v1/billing/summary`.

### 4. Reporte PDF y Despacho por Correo (Prioridad 4)
* **Stitch:** Modal con previsualización del veredicto, hash firmado, campo de correo destinatario y botón "Generar PDF y Enviar".
* **Base de Datos:** 🟢 Cero cambios (opcional `dispatch_logs`).
* **Backend:** 
  * Endpoint `GET /api/v1/evaluations/{id}/pdf` (usando `reportlab` o generación PDF en frontend).
  * Endpoint `POST /api/v1/evaluations/{id}/email` (usando `smtplib` / mock de despacho exitoso).

---

## 💬 Frase de Reanudación para el Nuevo Chat:
> *"Continuamos con SecureCode a partir de la memoria `SECURECODE-FRONTEND-ROADMAP-2026`. Todo el Flujo L.E.R. está listo y quedamos listos para arrancar con el Historial de Ejecuciones (Fase 2)."*

