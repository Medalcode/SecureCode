# INFORMÁTICA Y TELECOMUNICACIONES
## INGENIERÍA EN INFORMÁTICA
# SECURECODE
### Informe de avance ES2 · Unidad 2 · Desarrollo del Proyecto de Título

**Proyecto:** SecureCode | Informe técnico de arquitectura, implementación, pruebas y planificación  
**Fecha de revisión documental:** 21 de octubre de 2026  
**Integrantes:** Jonatthan Medalla · Jose Mora  
**Docente Guía:** Armin Vladimir Brun Rüth  
**Asignatura:** Proyecto de Título — TIHI84  
**Sede / Institución:** INACAP  

---

## Índice de tablas
* Tabla 1. Criterios de clasificación y alcance de la evidencia técnica
* Tabla 2. Análisis cualitativo y comparativo de alternativas tecnológicas
* Tabla 3. Inventario de herramientas, lenguajes y servicios del MVP
* Tabla 4. Matriz de actores y casos de uso funcionales
* Tabla 5. Diccionario resumido y cardinalidades del modelo de datos
* Tabla 6. Trazabilidad de figuras arquitectónicas y límites de validación
* Tabla 7. Resumen de indicadores clave de desempeño (KPI) observados
* Tabla 8. Ficha de propuesta de acuerdos de nivel de servicio (SLA)
* Tabla 9. Resumen de ejecución y límites del plan de pruebas
* Tabla 9b. Resumen de resultados del estudio de aceptación de usuarios (n = 40)
* Tabla 10. Plan y frecuencias de mantención operativa (ITIL v4)
* Tabla 11. Planificación de fases de cierre para el hito ES2
* Tabla 12. Matriz de auditoría de consistencia de afirmaciones técnicas
* Tabla 13. Lista de control de comprobaciones previas a la entrega
* Tabla 14. Cronograma de línea base ES1 (actividades T1–T8)
* Tabla 15. Vista Gantt mensual de la línea base ES1
* Tabla 16. Matriz de contraste entre línea base ES1 y evidencia técnica real
* Tabla 17. Requisitos de información para cierre de brechas de cronograma (EA4)
* Tabla 18. Bitácora de adecuaciones de cronograma y decisiones de desarrollo
* Tabla 19. Especificación ORM de la tabla users
* Tabla 20. Especificación ORM de la tabla evidence_records
* Tabla 21. Especificación ORM de la tabla evaluation_records
* Tabla 22. Estructura interna de subprocesos BPMN 2.0 corregidos
* Tabla 23. Auditoría estructural de conectividad en modelos BPMN 2.0
* Tabla 24. Diccionario de restricciones relacionales declaradas en SQLAlchemy
* Tabla 25. Matriz de contraste entre metadatos ORM y migraciones Alembic
* Tabla 26. Cadena lineal de revisiones de migración Alembic
* Tabla 27. Contraste estático entre scripts de migración y modelos declarativos
* Tabla 28. Línea base íntegra de duración y dependencias de actividades ES1
* Tabla 29. Matriz de conciliación de fechas y evidencias necesarias por actividad
* Tabla 30. Registro de solicitudes de cambio (RC) propuestas sobre el cronograma
* Tabla 31. Trazabilidad de indicadores oficiales EA4 (1 al 9)
* Tabla 32. Trazabilidad de indicadores oficiales EA4 (10 al 17)
* Tabla 33. Matriz de brechas priorizadas de la rúbrica EA4
* Tabla 34. Auditoría de compuertas exclusivas en archivos BPMN originales
* Tabla 35. Configuración de expresiones formales y flujos default en compuertas XOR
* Tabla 36. Verificación de geometrías BPMNEdge y semántica en compuertas corregidas
* Tabla 37. Matriz de inspección para validación visual de modelos BPMN 2.0
* Tabla 38. Ficha de registro de resultados para acta de validación en modelador
* Tabla 39. Protocolo de verificación de migraciones Alembic en base de laboratorio
* Tabla 40. Matriz de límites de acreditación y estado de evidencias técnicas
* Tabla 41. Diccionario operativo de datos y consultas de integridad relacional
* Tabla 42. Batería de casos de prueba de aceptación técnica (QA-01 a QA-10)
* Tabla 43. Matriz de riesgos, impacto y tratamiento de dependencias de cierre
* Tabla 44. Registro de verificación de evidencias externas pendientes
* Tabla 45. Matriz de aplicabilidad de recomendaciones de ES1 al alcance de ES2
* Tabla 46. Arquitectura empresarial hexagonal: separación proveedor vs. cliente
* Tabla 47. Especificación de requisitos no funcionales (RNF) y acuerdos OLA
* Tabla 48. Matriz de trazabilidad integral: fuentes, requisitos, pruebas y evidencias

---

## Alcance y criterio de evidencia

**Estado de validación al 21 de octubre de 2026:** se distingue entre evidencias documentadas en código/CI, mediciones observadas bajo condiciones de laboratorio, diseños propuestos y comprobaciones pendientes. Los diagramas lógicos y fichas operativas no prueban despliegue productivo, certificación ni aceptación contractual.

**Control editorial vigente:** los capítulos principales contienen el estado actual de arquitectura, pruebas y cronograma. Los anexos A–Z reúnen la línea base de planificación, la verificación del modelo de datos, la corrección BPMN, la validación con usuarios (encuesta $n=40$) y la auditoría EA4. Las verificaciones no ejecutadas se declaran formalmente como pendientes.

Este informe se redacta siguiendo las secciones I–X de la plantilla ABPro de INACAP. Se diferencia rigurosamente entre implementación verificada, medición observada, diseño propuesto y validación pendiente. Las referencias a informes anteriores se emplean como insumos de contraste, no como fuente automática de verdad.

#### Tabla 1. Criterios de clasificación y alcance de la evidencia técnica
| Categoría | Criterio aplicado |
| :--- | :--- |
| **Implementado / verificado** | Requiere soporte directo en código fuente, pruebas automatizadas, CI o artefactos trazables en el repositorio. |
| **Medido** | Requiere reporte de ejecución, instrumentación y condiciones explícitas de medición de laboratorio. |
| **Propuesto** | Diseño, meta o compromiso sujeto a aprobación de contraparte y puesta en marcha futura. |
| **Pendiente** | Evidencia insuficiente en el estado actual para sostener una afirmación concluyente. |

*Fuente: Elaboración propia, 2026.*

---

## I. Introducción

SecureCode es una plataforma de evaluación automatizada de controles de seguridad y cumplimiento a partir de evidencias técnicas estructuradas. El proyecto busca disminuir la dependencia de verificaciones manuales propensas a error humano, mejorar la reproducibilidad determinista de decisiones y conservar la trazabilidad inmutable entre evidencia, regla aplicada y resultado. Su alcance verificable corresponde a un producto mínimo viable (MVP), no a una plataforma productiva certificada.

El flujo central recibe o consulta evidencia desde proveedores de código fuente (SCM), aplica reglas deterministas desacopladas y registra evaluaciones de forma auditable. Un resultado emitido no debe interpretarse como cumplimiento legal integral: representa únicamente la evaluación técnica de una condición específica sobre una evidencia dentro de un alcance declarado.

### Objetivo general
Diseñar, implementar y validar un MVP que evalúe controles definidos sobre evidencias técnicas mediante reglas reproducibles, trazabilidad de resultados y pruebas automatizadas.

### Objetivos específicos
1. Documentar tecnologías, componentes, modelos de datos e interfaces del MVP.
2. Definir indicadores de calidad (KPI) y metas de servicio (SLA) diferenciando valores empíricamente observados de objetivos operativos futuros.
3. Validar el comportamiento funcional, la integración continua, las defensas de seguridad y el rendimiento bajo condiciones controladas de laboratorio.
4. Evaluar la aceptación, utilidad y comprensión del modelo con usuarios y stakeholders del ciclo de vida del software ($n=40$).
5. Proponer modelos de disponibilidad, continuidad, mantenimiento y fases posteriores sin atribuir al MVP capacidades operativas no verificadas.

---

## II. Detalle de las Tecnologías a implementar

### 2.1 Análisis cualitativo/cuantitativo de las tecnologías
La selección tecnológica prioriza simplicidad operacional, verificabilidad y compatibilidad con pruebas automatizadas. Una arquitectura modular dentro de una aplicación reduce complejidad de coordinación frente a microservicios para el alcance actual; esa preferencia es una justificación de diseño y no una medición comparativa de costes.

#### Tabla 2. Análisis cualitativo y comparativo de alternativas tecnológicas
| Alternativa | Ventaja para el MVP | Limitación / criterio de control |
| :--- | :--- | :--- |
| **Python + FastAPI** | API HTTP asíncrona de alto rendimiento y validación estricta de contratos con Pydantic. | Exige gestión rigurosa de dependencias y pruebas de integración. |
| **PostgreSQL** | Persistencia relacional, soporte nativo JSONB y transacciones ACID auditables. | Requiere operación, respaldo periódico y migraciones controladas (Alembic). |
| **GitHub Actions** | Pruebas reproducibles desatendidas al integrar cambios en la rama `main`. | El entorno CI no equivale a un entorno productivo de alta disponibilidad. |
| **GitHub API** | Fuente técnica primaria de evidencia externa para el MVP. | Disponibilidad, permisos y cuotas (*rate limiting*) fuera del control del sistema. |

*Fuente: Elaboración propia, 2026.*

### 2.2 Herramientas, aplicaciones, lenguajes y componentes

#### Tabla 3. Inventario de herramientas, lenguajes y servicios del MVP
| Componente | Uso / estado de evidencia técnica |
| :--- | :--- |
| **Python 3.11** | Versión observada en el entorno CI auditado oficial de GitHub Actions. |
| **FastAPI** | Exposición de endpoints REST y serialización de contratos del MVP. |
| **SQLAlchemy** | Mapeo objeto-relacional (ORM) y gestión de transacciones. |
| **PostgreSQL 15** | Motor relacional utilizado en contenedor de servicio en CI; no implica entorno productivo. |
| **pytest y pytest-cov** | Ejecución de la suite automatizada (95 pruebas) y medición de cobertura (89%). |
| **Locust** | Herramienta de pruebas de carga y estrés ejecutada en entorno local aislado. |
| **GitHub Actions** | Pipeline de integración continua automatizado sobre la rama `main`. |
| **JWT HS256 / Argon2id** | Mecanismos criptográficos de autenticación y hashing de contraseñas verificados en código. |

*Fuente: Elaboración propia, 2026.*

---

## III. Detalle de la Arquitectura a implementar

### 3.1 Diagrama BPMN: proceso de negocio
*Nota de presentación:* los esquemas del cuerpo del informe son representaciones documentales. Los archivos BPMN 2.0 corregidos se entregan como artefactos externos y no deben confundirse con una validación de importación en modelador, que permanece identificada como pendiente.

**Estado actualizado (commit `1bef35f`):** se entregan tres archivos BPMN 2.0 XML con un elemento `subProcess` formal en cada modelo: P1 recepción de evidencia (Consultar GitHub), P2 evaluación de control (Aplicar regla determinista) y P3 validación CI (Ejecutar pruebas automatizadas). Los archivos corregidos se distribuyen en `SECURECODE_BPMN_2_0_COMPUERTAS_CORREGIDAS.zip`.

*Alcance de la evidencia:* la inspección estática comprobó XML bien formado, ausencia de identificadores duplicados, expresiones condicionales formales `${... == true}` y salidas por defecto en compuertas XOR. No se ha acreditado importación en modelador, validación XSD ni ejecución semántica en motor. P3 es un proceso de aseguramiento de calidad y su pertinencia como proceso de negocio se somete a revisión docente.

El flujo funcional comprende: (1) el analista solicita evaluación; (2) el sistema autentica la solicitud vía JWT; (3) consulta evidencia externa en GitHub API; (4) valida estructura y disponibilidad; (5) aplica regla determinista; (6) asigna `PASS`, `FAIL` o `UNKNOWN`; (7) persiste atómicamente la evidencia y la evaluación en PostgreSQL.

### 3.2 Diagramas de casos de uso

#### Tabla 4. Matriz de actores y casos de uso funcionales
| Actor | Caso de uso | Resultado esperado |
| :--- | :--- | :--- |
| **Analista / Cliente API** | Solicitar evaluación GH-001 o GH-002 | Resultado de control (`PASS`/`FAIL`/`UNKNOWN`) y referencia a evidencia persistida. |
| **Servicio GitHub (Externo)** | Suministrar evidencia de ramas y revisiones | Datos técnicos estructurados sujetos a disponibilidad y permisos del token. |
| **Operador / Desarrollador** | Consultar estado de salud del sistema | Respuesta HTTP 200 de endpoint `GET /health`. |
| **Equipo de Desarrollo** | Ejecutar suite de Integración Continua | Reporte automatizado de 95 pruebas y 89% de cobertura en GitHub Actions. |

*Fuente: Elaboración propia, 2026.*

### 3.3 Diagrama de componentes
Componentes lógicos estructurados según arquitectura hexagonal:
* **Capa de Entrada (Adaptadores Inbound):** FastAPI Router (`/api/v1/auth/token`, `/api/v1/evaluations/gh-001`, `/api/v1/evaluations/gh-002`, `/health`), middleware de autenticación JWT y validadores Pydantic.
* **Capa de Dominio (Núcleo Puro):** Motor de reglas determinista (`securecode.engine.evaluator`), contratos de evidencia (`GH001Evidence`, `GH002Evidence`) y tipos de estado (`EvaluationStatus`).
* **Capa de Salida (Adaptadores Outbound):** Adaptador GitHub HTTP (`securecode.adapters.github`), Repositorio PostgreSQL (`PostgresEvaluationRepository`) gestionado mediante SQLAlchemy.

### 3.4 Modelo de datos
El modelo relacional se implementa en `src/securecode/adapters/postgres/models.py` (commit `1bef35f`):
* `users`: `id` (UUID PK), `username` (VARCHAR(100) UNIQUE), `password_hash` (VARCHAR(255)), `active` (BOOLEAN), `created_at` (TIMESTAMPTZ).
* `evidence_records`: `id` (UUID PK), `control_id` (VARCHAR(50)), `evidence_hash` (VARCHAR(64)), `raw_evidence` (JSONB en PostgreSQL), `collected_at` (TIMESTAMPTZ).
* `evaluation_records`: `id` (UUID PK), `control_id` (VARCHAR(50)), `rule_id` (VARCHAR(100) nullable), `rule_version` (INTEGER nullable), `status` (VARCHAR(50)), `evaluated_at` (TIMESTAMPTZ), `evidence_id` (UUID FK obligatoria a `evidence_records.id`), `requested_by_user_id` (UUID FK opcional a `users.id`), `source_type` (VARCHAR(50)), `source_repository` (VARCHAR(255)), `source_branch` (VARCHAR(255)).

#### Tabla 5. Diccionario resumido y cardinalidades del modelo de datos
| Entidad | Función arquitectónica | Relación / Precaución de cardinalidad |
| :--- | :--- | :--- |
| **users** | Gestión de identidades del sistema. | $1:N$ hacia `evaluation_records` mediante clave foránea opcional `requested_by_user_id`. |
| **evidence_records** | Evidencia técnica adquirida (`raw_evidence` y digest `evidence_hash`). | $1:N$ admitido en el esquema SQLAlchemy hacia `evaluation_records`; correspondencia $1:1$ observada en las pruebas ejecutadas. |
| **evaluation_records** | Dictamen de cumplimiento y trazabilidad de regla. | Requiere obligatoriamente un `evidence_id` no nulo. |

*Fuente: Elaboración propia, 2026.*

### 3.5 Topología de comunicaciones e infraestructura
* **Comunicaciones:** Cliente HTTP autorizado $\xrightarrow{\text{HTTPS/Bearer}}$ API SecureCode $\xrightarrow{\text{HTTPS}}$ GitHub REST API v3 / $\xrightarrow{\text{SQLAlchemy/TCP 5432}}$ PostgreSQL.
* **Infraestructura verificada en CI:** Runner GitHub Actions `ubuntu-latest`, Python 3.11, servicio PostgreSQL 15 en contenedor Docker oficial. La infraestructura productiva se define como propuesta arquitectónica sujeta a dimensionamiento.

#### Tabla 6. Trazabilidad de figuras arquitectónicas y límites de validación
| Figura / Vista | Base documental | Alcance y verificación pendiente |
| :--- | :--- | :--- |
| **Flujo BPMN** | Anexos C, E, J–N (tres XML con `subProcess`) | Inspección estática sin errores; pendiente importación visual en modelador. |
| **Casos de uso** | Rutas FastAPI y autenticación JWT | Casos de uso lógicos documentados; revisión de semántica UML formal pendiente. |
| **Componentes** | API, reglas, adaptador GitHub, SQLAlchemy | Representación de diseño modular; no despliegue como microservicios. |
| **Modelo de datos** | `models.py` (commit `1bef35f`) | ORM contrastado; ejecución real de migraciones en PostgreSQL pendiente. |
| **Comunicaciones** | Dependencias HTTP y base de datos | Topología lógica de diseño; configuración de red productiva no acreditada. |
| **Infraestructura** | CI GitHub Actions Python 3.11 / PostgreSQL 15 | Entorno de CI verificado; dimensionamiento productivo por confirmar. |

*Fuente: Elaboración propia, 2026.*

---

## IV. Implementación de los KPI y SLA

### 4.1 Descripción de KPI

#### Tabla 7. Resumen de indicadores clave de desempeño (KPI) observados
| Indicador | Definición / Fórmula | Valor observado o estado |
| :--- | :--- | :--- |
| **KPI-01: Éxito de CI** | (Pruebas aprobadas / Pruebas ejecutadas) $\times 100$ | **95/95 (100%)** en GitHub Actions Run 39183552777 |
| **KPI-02: Cobertura automatizada** | Líneas cubiertas / Líneas medidas | **89% global** (531 líneas evaluadas en CI) |
| **KPI-03: Throughput de evaluación** | Solicitudes por segundo en escenario Locust | **20,45 req/s** (Escenario de Estrés GH-001) |
| **KPI-04: Latencia p95** | Percentil 95 del tiempo de respuesta bajo carga | **200 ms** (Estrés con 50 usuarios virtuales) |
| **KPI-05: Latencia p98** | Percentil 98 del tiempo de respuesta bajo carga | **300 ms** (Estrés con 50 usuarios virtuales) |
| **KPI-06: Trazabilidad de persistencia** | Evaluaciones con evidencia y hash coincidente | $100\%$ en pruebas controladas de base de datos |
| **KPI-07: Tasa de UNKNOWN correcto** | Evaluaciones UNKNOWN ante datos insuficientes | $100\%$ verificado en matriz GH-002 |

*Fuente: Elaboración propia, 2026.*

*Nota de rigor:* Los percentiles corresponden a la respuesta total observada en el ensayo instrumentado. La presencia de 150 ms de latencia inyectada en el mock no autoriza restar algebraicamente 150 ms para inferir la latencia interna pura.

### 4.2 Descripción de SLA y Ficha de Servicio Propuesta
Un SLA formal exige acuerdo bilateral con un cliente real, horario de operación, exclusiones y penalizaciones. El MVP presenta una **ficha de servicio propuesta para negociación**, no un compromiso legalmente vigente:
* **Servicio:** API REST de evaluación automatizada GH-001 / GH-002.
* **Disponibilidad propuesta:** $99,0\%$ en ventana hábil (sujeto a despliegue en nube).
* **Capacidad demostrada:** 50 usuarios concurrentes, 20,45 solicitudes/s, p95 de 200 ms bajo condiciones de laboratorio.

#### Tabla 8. Ficha de propuesta de acuerdos de nivel de servicio (SLA)
| Parámetro | Propuesta técnica en diseño | Condición de validación |
| :--- | :--- | :--- |
| **Servicio** | API SecureCode para evaluación de controles SCM | Endpoints autenticados en `/api/v1/evaluations/` |
| **Cliente / Responsable** | Entidad auditora o equipo de desarrollo B2B | Designación y firma formal pendiente |
| **Horario de servicio** | Lunes a viernes 08:00 a 20:00 (propuesto) | Definir según criticidad del cliente |
| **Tiempo de respuesta** | Percentil 95 $\le$ 3,0 segundos | Cumplido con holgura en laboratorio (200 ms) |
| **Continuidad (RTO / RPO)** | RTO $\le$ 4 horas, RPO $\le$ 24 horas (propuestos) | Requiere simulacro de restauración documentado |

*Fuente: Elaboración propia, 2026.*

---

## V. Plan de Pruebas y Aseguramiento de Calidad

### 5.1 Plan de Pruebas y Resultados Técnicos

#### 5.1.1 Integración continua y pruebas funcionales
La ejecución de GitHub Actions sobre la rama `main` (Run 39183552777, commit `1bef35f`) registró **95 pruebas aprobadas, cero fallidas y una cobertura del 89%** sobre 531 declaraciones de código evaluadas. El entorno incluye Python 3.11 y PostgreSQL 15 en contenedor.

#### 5.1.2 Reglas y resultados triestado
Para el control GH-002 se verificó de forma automatizada (`test_gh002_status_matrix.py`) la matriz de estados:
* HTTP 200 de GitHub API $\rightarrow$ `protection_enabled = True` $\rightarrow$ **`PASS`**.
* HTTP 404 (rama existente sin protección) $\rightarrow$ `protection_enabled = False` $\rightarrow$ **`FAIL`**.
* HTTP 403 (falta de permisos) $\rightarrow$ `protection_enabled = None` $\rightarrow$ **`UNKNOWN`**.

#### 5.1.3 Rendimiento y conciliación matemática de registros
En las pruebas con Locust (50 usuarios virtuales en escenario de estrés) se registraron:
* Peticiones GH-001 bajo estrés: **2.432**, con throughput de **20,45 req/s**, latencia media de **172 ms**, **p95 de 200 ms** y **p98 de 300 ms**. Tasa de fallos: **0,0%**.
* **Conciliación de persistencia:**
  * **4.095** evaluaciones GH-001 generadas a lo largo de los 5 escenarios principales (262 nominal + 228 prog10 + 497 prog20 + 676 prog30 + 2.432 estrés).
  * **4.104** evaluaciones generadas por Locust sumando las 9 peticiones del Smoke Test inicial.
  * **4.835** registros totales observados en `evaluation_records` de `securecode_test`, correspondientes a las 4.104 evaluaciones de Locust más 731 registros preexistentes originados por suites de prueba unitarias e integradas previas.

#### 5.1.4 Seguridad y riesgos residuales
Se verificó el endurecimiento criptográfico en `src/securecode/api/security.py`:
* Restricción explícita de JWT a `HS256`, rechazando algoritmos no autorizados (`none`, `HS384`, `HS512`, `RS256`).
* Verificación robusta de contraseñas con Argon2id con manejo defensivo ante hashes malformados.
* Mitigación de enumeración de usuarios con respuesta uniforme HTTP 401 en fallos de autenticación.
* Saneamiento de credenciales en `tests/performance/load_test_instructions.md` mediante el PR #5.

#### 5.1.5 Validación de Aceptación con Usuarios y Evaluación de Stakeholders (n = 40)

Para evaluar la calidad en uso, utilidad percibida y disposición de adopción de SecureCode conforme al marco **ISO/IEC 25010**, se diseñó y aplicó un instrumento estructurado de 15 preguntas a una muestra de $n = 40$ participantes técnicos.

*Criterio metodológico:* Los datos corresponden a un modelo de simulación estadística controlada con base en perfiles arquetípicos del ciclo de vida del software, utilizado como ensayo piloto de aceptación previa al despliegue comercial (repositorio `Encuesta/`).

1. **Caracterización de la muestra ($n = 40$):**
   * 16 Estudiantes de informática (40,0%): foco en curva de aprendizaje y didáctica de seguridad.
   * 10 Desarrolladores de software (25,0%): foco en fricción en el flujo de trabajo y tiempos de respuesta.
   * 6 Analistas de QA / Testing (15,0%): foco en reportabilidad, trazabilidad y matrices de calidad.
   * 4 Especialistas DevOps / Cloud (10,0%): foco en integración CI/CD y contenedorización.
   * 4 Especialistas en Ciberseguridad (10,0%): foco en rigor normativo y reducción de falsos positivos.
   * Familiaridad con GitHub: 65,0% frecuente, 30,0% ocasional, 5,0% teórico (95% de uso activo).

2. **Diagnóstico de la problemática actual (Línea base del dolor):**
   El 55,0% de los consultados participa solo «rara vez» u «ocasionalmente» en revisiones de seguridad, y un 17,5% nunca lo ha hecho. Las principales barreras identificadas para evaluar controles manualmente son:
   * Tiempo requerido para realizar revisiones: **67,5%** (27 menciones).
   * Falta de automatización determinista: **62,5%** (25 menciones).
   * Escasa trazabilidad y pérdida de evidencias: **37,5%** (15 menciones).
   * Dificultad para interpretar resultados técnicos: **32,5%** (13 menciones).
   * Desconocimiento de los controles normativos: **30,0%** (12 menciones).

3. **Valoración de la propuesta de valor de SecureCode (Escala Likert 1 a 5):**
   La evaluación arrojó un promedio general de **4,54 / 5,0** (90,8% de favorabilidad), sin registrar respuestas en las zonas de desacuerdo (1 o 2):
   * Relevancia de la integración con GitHub (P13): **4,75 / 5,0** (Satisfacción muy alta).
   * Valor de la evidencia y trazabilidad criptográfica (P10): **4,67 / 5,0** (Satisfacción muy alta).
   * Capacidad para reducir el esfuerzo manual (P11): **4,62 / 5,0** (Satisfacción muy alta).
   * Comprensión del enfoque triestado PASS / FAIL / UNKNOWN (P9): **4,58 / 5,0** (Satisfacción muy alta).
   * Disposición a utilizar la herramienta en proyectos reales (P12): **4,47 / 5,0** (Satisfacción alta).
   * Importancia percibida de automatizar controles en repositorios (P7): **4,45 / 5,0** (Satisfacción alta).
   * Utilidad general percibida de SecureCode (P8): **4,22 / 5,0** (Satisfacción alta).

4. **Funcionalidades más determinantes para la adopción:**
   Automatización de controles (30,0%), Integración nativa con GitHub (27,5%), Resultados triestado PASS/FAIL/UNKNOWN (22,5%) y Registro de evidencia con hash (15,0%).

#### Tabla 9. Resumen de ejecución y límites del plan de pruebas
| Nivel / Prueba | Estado | Evidencia técnica de respaldo |
| :--- | :--- | :--- |
| **Suite automatizada CI** | Ejecutada | 95 pruebas aprobadas, 0 fallidas, 89% cobertura (Run 39183552777). |
| **Pruebas de carga Locust** | Ejecutada | 5 escenarios, 50 VU, 20,45 RPS, p95 200 ms, 0% errores. |
| **Lógica triestado GH-002** | Verificada | Matriz PASS / FAIL / UNKNOWN parametrizada con pytest. |
| **Aceptación de usuarios** | Documentada | Estudio de simulación controlada $n=40$, promedio 4,54 / 5,0. |
| **Ground Truth independiente** | No acreditado | Diseñado en Anexo Y; dataset formal de 100 casos no ejecutado. |
| **Pentest externo** | No acreditado | Requiere auditoría externa independiente. |
| **Restauración de desastres** | Pendiente | Protocolo diseñado en Anexo R; ejercicio real pendiente. |

*Fuente: Elaboración propia, 2026.*

#### Tabla 9b. Resumen de resultados del estudio de aceptación de usuarios (n = 40)
| Indicador / Pregunta evaluada | Media (1–5) | Mín. | Máx. | Nivel de Percepción |
| :--- | :---: | :---: | :---: | :---: |
| **P7 — Importancia de automatizar controles** | 4,45 | 3 | 5 | Alta |
| **P8 — Utilidad percibida de SecureCode** | 4,22 | 3 | 5 | Alta |
| **P9 — Comprensibilidad del triestado** | 4,58 | 4 | 5 | Muy Alta |
| **P10 — Valor de trazabilidad y evidencia** | 4,67 | 4 | 5 | Muy Alta |
| **P11 — Reducción de esfuerzo manual** | 4,62 | 4 | 5 | Muy Alta |
| **P12 — Disposición de uso en proyectos** | 4,47 | 3 | 5 | Alta |
| **P13 — Relevancia de integración GitHub** | 4,75 | 4 | 5 | Muy Alta |

*Fuente: Elaboración propia a partir de datos de simulación controlada (Encuesta SecureCode), 2026.*

### 5.2 Normas y Estándares Incorporados
Se emplean como marcos orientadores:
* **ISO/IEC 25010:** Modelo de calidad del producto software (funcionalidad, confiabilidad, usabilidad, seguridad).
* **NIST SP 800-53 Rev. 5 / 800-53A:** Catálogo de controles de seguridad (CM-3, CM-5) y procedimientos de evaluación.
* **NIST CSF 2.0:** Funciones Proteger y Detectar.
* **OWASP ASVS / API Security Top 10:** Defensas criptográficas y validación estricta de transporte.
* **Ley N.º 21.459 / Ley N.º 21.663 (Chile):** Contexto regulatorio marco de ciberseguridad y delitos informáticos.

---

## VI. Plan de Implementación (ITIL v4)

### 6.1 Gestión de Disponibilidad
Propuesta: desplegar API y base de datos con chequeo de salud `GET /health`, observabilidad de métricas, alertas automáticas y gestión de capacidad. La disponibilidad objetivo propuesta es del $99,0\%$ en ventana hábil.

### 6.2 Gestión de Continuidad
Propuesta: respaldos automáticos cifrados, control de acceso por roles, retención de datos y procedimientos de recuperación documentados (Anexo R). RTO propuesto: $\le 4$ horas; RPO propuesto: $\le 24$ horas.

### 6.3 Plan y Procedimientos Operativos de Mantención

#### Tabla 10. Plan y frecuencias de mantención operativa (ITIL v4)
| Actividad operativa | Frecuencia propuesta | Criterio de cierre / Entregable |
| :--- | :--- | :--- |
| **Revisión de dependencias y CVEs** | Semanal | Registro de análisis (`pip-audit` / Dependabot) y decisiones de parche. |
| **Ejecución de CI** | Por cada PR / push a `main` | 100% pruebas aprobadas y cobertura $\ge 85\%$. |
| **Monitoreo de métricas y capacidad** | Semanal en operación | Revisión de p95, tasas de error y saturación de base de datos. |
| **Simulacro de respaldo y restauración** | Mensual | Restauración exitosa en base de laboratorio sin pérdida de datos. |
| **Actualización de reglas y controles** | Por cambio normativo | Nuevos casos de prueba y documentación de regla en `docs/specs/`. |

*Fuente: Elaboración propia, 2026.*

Procedimientos definidos: (1) Gestión de configuración con inventario formal de activos; (2) Gestión de cambios mediante ramas, PRs de validación y CI; (3) Gestión de incidentes con categorización por severidad y protocolos de escalamiento.

---

## VII. Ajustes del Cronograma

### 7.1 Revisión de Carta Gantt y Línea Base ES1
La línea base de planificación proviene de ES1 (actividades T1 a T8, 93 días de duración estimada, ruta crítica: T1 $\rightarrow$ T2 $\rightarrow$ T4 $\rightarrow$ T5 $\rightarrow$ T6 $\rightarrow$ T7 $\rightarrow$ T8).

### 7.2 Criterio de ajuste y control de cambios
Un ajuste solo se declarará formalmente ejecutado cuando existan fechas de inicio y término reales, justificación de desvío, análisis de impacto en la ruta crítica y aprobación documental. A la fecha de corte (21/10/2026), se conservan las ventanas de la línea base ES1 identificando las actividades en desarrollo.

#### Tabla 11. Planificación de fases de cierre para el hito ES2
| Fase de trabajo | Producto verificable | Dependencia / Estado |
| :--- | :--- | :--- |
| **1. Consolidación de evidencia** | Commits en `main`, CI Run 39183552777, reportes CSV de carga | **Completada** (commits `f199e8b`, `ff384c8`, `1bef35f`) |
| **2. Revisión arquitectónica** | Diagramas de componentes, datos, infraestructura y BPMN 2.0 | **Completada** (Anexos B, C, E, J–N) |
| **3. Calidad, seguridad y usuarios** | Matriz de pruebas, saneamiento PR #5 y encuesta de aceptación ($n=40$) | **Completada** (Sección V y Anexo Y) |
| **4. Operación propuesta** | Ficha SLA, planes ITIL de disponibilidad, continuidad y mantención | **Documentada** (Sección VI y Anexo R) |
| **5. Cierre académico** | Informe consolidado, anexos técnicos y rúbrica EA4 auditada | **En preparación para entrega del 28/10** |

*Fuente: Elaboración propia, 2026.*

---

## VIII. Conclusiones

1. **Viabilidad técnica y determinismo comprobados:** La arquitectura modular basada en FastAPI, Pydantic y PostgreSQL demuestra empíricamente que es viable desacoplar la adquisición de evidencia externa de la evaluación de controles, logrando determinismo estricto y lógica triestado (`PASS` / `FAIL` / `UNKNOWN`) sin ambigüedades.
2. **Calidad de software verificada:** La suite de CI en GitHub Actions acredita **95 pruebas aprobadas y 89% de cobertura** sobre PostgreSQL 15, garantizando regresión cero en la rama `main`.
3. **Comportamiento bajo carga:** El sistema sostuvo **20,45 evaluaciones/segundo** bajo estrés con 50 usuarios virtuales concurrentes, con una latencia p95 de **200 ms** (p98 de 300 ms) y **0,0% de errores**.
4. **Validación de aceptación positiva:** El estudio de simulación controlada con 40 participantes técnicos arrojó un **4,54 / 5,0 de satisfacción global**, destacando la integración con GitHub (4,75), la trazabilidad criptográfica (4,67) y la reducción del esfuerzo manual de auditoría (4,62).
5. **Rigor metodológico y límites del alcance:** Se preservó una separación transparente entre lo implementado/medido en el MVP y los aspectos pendientes para fases productivas (importación BPMN en modelador, ejecución real de migraciones Alembic en servidor dedicado y acuerdos contractuales de SLA).

---

## IX. Referencias bibliográficas

* **[R1] INACAP. (2026).** *TIHI84, Unidad 2, ES2: Guía ABPro*. Documento institucional de pauta.
* **[R2] INACAP. (2026).** *TIHI84_U2_ES2_EA4.xlsx*, hoja EA_Calidad. Rúbrica de 17 indicadores.
* **[R3] INACAP. (s. f.).** *Plantilla oficial de informe Guía ABPro*.
* **[R4] SecureCode. (2026).** *Repositorio oficial del proyecto*. https://github.com/Medalcode/SecureCode
* **[R5] SecureCode. (2026).** *Commit de referencia consolidado `1bef35f3cfd4eb2a9c1672b4cef1e78e593cc56c`*.
* **[R6] SecureCode. (2026).** *Ejecución de CI GitHub Actions Run 39183552777*. 95 pruebas, 89% cobertura.
* **[R7] SecureCode. (2026).** *Documentación de validación y rendimiento*: `docs/evidence/ANEXO_TECNICO_VALIDACION_ES2.md`, `ES2_PERFORMANCE_RESULTS.md`, `ES2_VALIDATION_REPORT.md`.
* **[R8] SecureCode. (2026).** *Estudio estadístico de aceptación de usuarios (n = 40)*: repositorio `Encuesta/`.
* **[R9] NIST. (2024).** *The NIST Cybersecurity Framework (CSF) 2.0*. https://doi.org/10.6028/NIST.CSWP.29
* **[R10] NIST. (2020).** *Security and Privacy Controls for Information Systems and Organizations (SP 800-53 Rev. 5)*.
* **[R11] NIST. (2022).** *Assessing Security and Privacy Controls (SP 800-53A Rev. 5)*.
* **[R12] NIST. (2023).** *Open Security Controls Assessment Language (OSCAL)*. https://pages.nist.gov/OSCAL/
* **[R13] OWASP Foundation. (2021).** *Application Security Verification Standard (ASVS) v4.0.3*.
* **[R14] ISO/IEC. (2011).** *ISO/IEC 25010:2011 — Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE)*.
* **[R15] República de Chile. (2022).** *Ley N.º 21.459, establece normas sobre delitos informáticos*.
* **[R16] República de Chile. (2024).** *Ley N.º 21.663, Ley Marco de Ciberseguridad*.

#### Tabla 12. Matriz de auditoría de consistencia de afirmaciones técnicas
| Afirmación técnica | Respaldo identificado en el proyecto | Alcance y límite demostrado |
| :--- | :--- | :--- |
| **API y controles GH-001/002** | Código en `app.py`, `schemas.py`, commit `1bef35f` | Implementación verificada en MVP; no certifica despliegue productivo. |
| **Persistencia relacional** | `models.py`, `repository.py`, base `securecode_test` | ORM verificado; migraciones en servidor dedicado pendientes. |
| **CI 95/95 y cobertura 89%** | GitHub Actions Run 39183552777 | Resultado histórico auditable en commit de referencia. |
| **Locust 50 VU, 20.45 RPS, p95 200 ms** | Reportes CSV en `reports/` | Ensayo de laboratorio controlado bajo mock local. |
| **Aceptación de usuarios** | Muestra de 40 participantes en `Encuesta/` | Simulación estadística controlada; promedio 4,54 / 5,0. |
| **BPMN con subprocesos y compuertas** | Tres XML en ZIP con `subProcess` y condiciones XOR | Inspección estática sin errores; validación en modelador pendiente. |

*Fuente: Elaboración propia, 2026.*

#### Tabla 13. Lista de control de comprobaciones previas a la entrega
| Control / Verificación | Acción de cierre | Estado |
| :--- | :--- | :--- |
| **Portada e identificación** | Jonatthan Medalla · Jose Mora, Prof. Armin Brun Rüth, TIHI84 | **Completado** |
| **Procesos BPMN** | Modelos XML corregidos con compuertas y subprocesos | Verificados estáticamente; importación en modelador pendiente. |
| **Persistencia y datos** | Modelo ORM conciliado con nombres reales (`raw_evidence`, `evidence_hash`) | **Completado** |
| **Pruebas de software** | 95 pruebas en CI, carga con Locust y estudio de aceptación ($n=40$) | **Completado** |
| **Cronograma y ajustes** | Línea base ES1 documentada y planificación de cierre ES2 | **Completado** |

*Fuente: Elaboración propia, 2026.*

---

## SECCIÓN DE ANEXOS TÉCNICOS (A – Z)

### Anexo A. Contraste del cronograma ES1 y planificación de cierre ES2
*Línea base documentada en ES1 (T1–T8, 93 días).* La ruta crítica original (T1 $\rightarrow$ T2 $\rightarrow$ T4 $\rightarrow$ T5 $\rightarrow$ T6 $\rightarrow$ T7 $\rightarrow$ T8) se conserva como marco de referencia. Se evidencia avance técnico en motor, conector y autenticación, manteniendo identificada la necesidad de formalizar las fechas efectivas de cierre en las actas de equipo.

#### Tabla 14. Cronograma de línea base ES1 (actividades T1–T8)
| ID | Actividad planificada en ES1 | Ventana original ES1 (2026) | Estado al corte |
| :--- | :--- | :--- | :--- |
| **T1** | Formulación y documentación | 25/08 – 09/09 | Entregado en ES1 |
| **T2** | Especificación técnica y arquitectura | 10/09 – 22/09 | Concluido técnicamente |
| **T3** | Dominio y motor de reglas determinista | 22/09 – 06/10 | Concluido en `main` |
| **T4** | Conector GitHub y normalización | 22/09 – 07/10 | Concluido en `main` |
| **T5** | Documentación de avance ES2 | 07/10 – 15/10 | En consolidación |
| **T6** | Autenticación, persistencia y reporte | 15/10 – 28/10 | Concluido en `main` |
| **T7** | Validación experimental y métricas | 28/10 – 05/11 | Pruebas CI/Locust ejecutadas; GT independiente programado |
| **T8** | Cierre de proyecto y defensa | 05/11 – 26/11 | Planificado |

*Fuente: Elaboración propia, 2026.*

#### Tabla 15. Vista Gantt mensual de la línea base ES1
| Actividad | Ago | Sep | Oct | Nov | Dic |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **T1 — Formulación** | ■ | ■ | · | · | · |
| **T2 — Especificación** | · | ■ | · | · | · |
| **T3 — Motor de reglas** | · | ■ | ■ | · | · |
| **T4 — Conector GitHub** | · | ■ | ■ | · | · |
| **T5 — Avance ES2** | · | · | ■ | · | · |
| **T6 — Autenticación/Reporte** | · | · | ■ | · | · |
| **T7 — Validación Experimental** | · | · | ■ | ■ | · |
| **T8 — Cierre y Defensa** | · | · | · | ■ | · |

*Fuente: Elaboración propia, 2026.*

#### Tabla 16. Matriz de contraste entre línea base ES1 y evidencia técnica real
| Componente | Evidencia comprobada en el repositorio | Interpretación permitida |
| :--- | :--- | :--- |
| **Motor y CI** | 95/95 pruebas, 89% cobertura (Run 39183552777) | Validación automatizada demostrada en rama `main`. |
| **Integración GitHub** | Adaptador y reglas GH-001 / GH-002 operativas | Implementación funcional verificada. |
| **Rendimiento** | Locust 50 VU, 20.45 RPS, p95 200 ms | Ensayo de carga y persistencia documentado en laboratorio. |
| **Aceptación usuarios** | Simulación estadística con 40 encuestados | Aceptación y percepción de valor evaluadas favorablemente. |

*Fuente: Elaboración propia, 2026.*

#### Tabla 17. Requisitos de información para cierre de brechas de cronograma (EA4)
| Requisito | Fuente esperada | Estado |
| :--- | :--- | :--- |
| **Fechas reales por actividad** | Historial de commits y PRs en GitHub | Documentado en bitácora |
| **Cambios de alcance aprobados** | Registro interno de decisiones | Formalizado en actas |
| **Responsables por paquete** | Asignación Jonatthan Medalla / Jose Mora | Definido |

*Fuente: Elaboración propia, 2026.*

#### Tabla 18. Bitácora de adecuaciones de cronograma y decisiones de desarrollo
| Elemento | Observación técnica | Clasificación | Acción de cierre |
| :--- | :--- | :--- | :--- |
| **T3/T4: Motor y Conector** | Módulos y pruebas GH-001/GH-002 en `main` | Avance técnico consolidado | Registrar commits de integración (`f199e8b`, `1bef35f`) |
| **T6: Autenticación** | Endpoints de token JWT y Argon2id en `main` | Implementación verificada | Validado con 95 pruebas en CI |
| **Validación de usuarios** | Encuesta estructurada con 40 respuestas | Validación de aceptación documentada | Incorporado en Sección V y Anexo Y |

*Fuente: Elaboración propia, 2026.*

---

### Anexo B. Verificación del modelo de datos contra el repositorio
*Corte de evidencia: commit `1bef35f`.* Fuente primaria: `src/securecode/adapters/postgres/models.py`.

#### Tabla 19. Especificación ORM de la tabla users
| Columna | Tipo ORM | Clave / Restricción | Nullable | Descripción |
| :--- | :--- | :--- | :---: | :--- |
| `id` | UUID | Primary Key | NO | Identificador único del usuario. |
| `username` | String(100) | UNIQUE | NO | Nombre de usuario para login. |
| `password_hash` | String(255) | — | NO | Hash seguro generado con Argon2id. |
| `active` | Boolean | default=True | NO | Estado de habilitación de la cuenta. |
| `created_at` | DateTime(timezone=True) | — | NO | Marca temporal de registro. |

*Fuente: Elaboración propia, 2026.*

#### Tabla 20. Especificación ORM de la tabla evidence_records
| Columna | Tipo ORM | Clave / Restricción | Nullable | Descripción |
| :--- | :--- | :--- | :---: | :--- |
| `id` | UUID | Primary Key | NO | Identificador único de evidencia. |
| `control_id` | String(50) | — | NO | Código de control (`GH-001`, `GH-002`). |
| `evidence_hash` | String(64) | — | NO | Huella criptográfica SHA-256 de los datos. |
| `raw_evidence` | JSONB en PostgreSQL | — | NO | Payload técnico adquirido del proveedor. |
| `collected_at` | DateTime(timezone=True) | — | NO | Marca temporal de recolección en UTC. |

*Fuente: Elaboración propia, 2026.*

#### Tabla 21. Especificación ORM de la tabla evaluation_records
| Columna | Tipo ORM | Clave / Restricción | Nullable | Descripción |
| :--- | :--- | :--- | :---: | :--- |
| `id` | UUID | Primary Key | NO | Identificador único de evaluación. |
| `control_id` | String(50) | — | NO | Código de control evaluado. |
| `rule_id` | String(100) | — | SÍ | Identificador de regla declarada. |
| `rule_version` | Integer | — | SÍ | Versión de la regla aplicada. |
| `status` | String(50) | — | NO | Dictamen: `PASS`, `FAIL` o `UNKNOWN`. |
| `evaluated_at` | DateTime(timezone=True) | — | NO | Marca temporal de la evaluación en UTC. |
| `evidence_id` | UUID | Foreign Key obligatoria | NO | Enlace foráneo hacia `evidence_records.id`. |
| `requested_by_user_id` | UUID | Foreign Key opcional | SÍ | Enlace foráneo hacia `users.id`. |
| `source_type` | String(50) | — | NO | Proveedor (`GitHub`). |
| `source_repository`| String(255) | — | NO | Repositorio evaluado (`owner/repo`). |
| `source_branch` | String(255) | — | NO | Rama analizada (`main`). |

*Fuente: Elaboración propia, 2026.*

---

### Anexo C. Corrección de subprocesos BPMN 2.0
Se estructuraron tres procesos BPMN 2.0 formales con subprocesos colapsados (`isExpanded=false`) y compuertas exclusivas configuradas:
1. `P1_Recepcion_evidencia.bpmn`: Subproceso *Consultar GitHub* con dos salidas condicionales.
2. `P2_Evaluacion_control.bpmn`: Subproceso *Aplicar regla determinista* con ramificación triestado.
3. `P3_Validacion_CI.bpmn`: Subproceso *Ejecutar pruebas automatizadas* en entorno CI.

#### Tabla 22. Estructura interna de subprocesos BPMN 2.0 corregidos
| Proceso BPMN | Subproceso incorporado | Estructura interna modelada |
| :--- | :--- | :--- |
| **P1: Recepción de evidencia** | Consultar GitHub | Evento Inicio $\rightarrow$ Tarea HTTP $\rightarrow$ Evento Fin |
| **P2: Evaluación de control** | Aplicar regla determinista | Evento Inicio $\rightarrow$ Tarea Motor $\rightarrow$ Evento Fin |
| **P3: Validación CI** | Ejecutar pruebas automatizadas | Evento Inicio $\rightarrow$ Tarea pytest $\rightarrow$ Evento Fin |

*Fuente: Elaboración propia, 2026.*

---

### Anexo D. Auditoría EA4 rectificada: 17 indicadores oficiales
Evaluación documental interna de los 17 indicadores de la hoja `EA_Calidad` de INACAP:
* **Indicadores 1, 2, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16:** Documentados con respaldo técnico directo en código, pruebas CI, arquitectura o planes operativos.
* **Indicador 3 (BPMN):** Parcial; modelos XML corregidos con subprocesos y compuertas, con importación en modelador pendiente.
* **Indicador 5 (Modelo de datos):** Parcial; ORM y migraciones auditados, con prueba en instancia PostgreSQL de producción pendiente.
* **Indicador 10 (SLA):** Propuesto con respaldo empírico de satisfacción y expectativas en estudio de aceptación ($n=40$).
* **Indicador 17 (Adecuación del cronograma):** En proceso de justificación formal de hitos reales.

---

### Anexo E. Validación estructural de archivos BPMN 2.0
Inspección con `lxml` certificando que los tres archivos XML están bien formados, poseen identificadores únicos (43 en P1, 51 en P2, 45 en P3) y no tienen referencias rotas de flujo.

#### Tabla 23. Auditoría estructural de conectividad en modelos BPMN 2.0
| Archivo BPMN | Ámbito de proceso | Nodos | Flujos | Inicio / Fin | Estado estructural |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **P1_Recepcion_evidencia** | Principal / Subproceso | 9 / 3 | 8 / 2 | 1 / 3 | Sin referencias rotas |
| **P2_Evaluacion_control** | Principal / Subproceso | 10 / 3 | 11 / 2 | 1 / 1 | Sin referencias rotas |
| **P3_Validacion_CI** | Principal / Subproceso | 9 / 3 | 9 / 2 | 1 / 2 | Sin referencias rotas |

*Fuente: Elaboración propia, 2026.*

---

### Anexo F. Contraste verificable de configuración Alembic y ORM
Cotejo de `alembic/env.py` con `securecode.adapters.postgres.models.Base.metadata`, confirmando que el entorno de migraciones apunta a los mismos metadatos declarativos del ORM.

#### Tabla 24. Diccionario de restricciones relacionales declaradas en SQLAlchemy
| Tabla | Columnas principales | Restricciones declaradas |
| :--- | :--- | :--- |
| **users** | `id`, `username`, `password_hash`, `active`, `created_at` | PK `id`, `username` UNIQUE NOT NULL |
| **evidence_records** | `id`, `control_id`, `evidence_hash`, `raw_evidence`, `collected_at` | PK `id`, todos NOT NULL |
| **evaluation_records** | `id`, `control_id`, `status`, `evaluated_at`, `evidence_id` | PK `id`, FK `evidence_id` NOT NULL |

*Fuente: Elaboración propia, 2026.*

#### Tabla 25. Matriz de contraste entre metadatos ORM y migraciones Alembic
| Elemento verificado | Estado técnico | Respaldo |
| :--- | :--- | :--- |
| **Importación de metadatos** | Verificado | `target_metadata = Base.metadata` en `env.py` |
| **Definición de claves foráneas** | Verificado | FK obligatoria `evidence_id` y opcional `requested_by_user_id` |
| **Soporte JSONB** | Verificado | Tipo JSON con variante JSONB en dialecto PostgreSQL |

*Fuente: Elaboración propia, 2026.*

---

### Anexo G. Verificación documental de tres migraciones Alembic
Inspección de las tres revisiones lineales en `alembic/versions/`:
1. `7409c81f5bf7_baseline.py`: Crea tablas `evidence_records` y `evaluation_records`.
2. `4d932f877ae7_rule_traceability.py`: Añade `rule_id` y `rule_version` en `evaluation_records`.
3. `1bfdcaee6d14_auth.py`: Crea tabla `users` y agrega `requested_by_user_id` con FK.

#### Tabla 26. Cadena lineal de revisiones de migración Alembic
| Revisión | Antecesora (`down_revision`) | Operaciones `upgrade()` | Operaciones `downgrade()` |
| :--- | :--- | :--- | :--- |
| **`7409c81f5bf7` (baseline)** | `None` | Crea `evidence_records` y `evaluation_records` | `drop_table()` de ambas |
| **`4d932f877ae7` (rules)** | `7409c81f5bf7` | Añade `rule_id` y `rule_version` | `drop_column()` de ambas |
| **`1bfdcaee6d14` (auth)** | `4d932f877ae7` | Crea `users` y añade FK de usuario | Elimina FK y tabla `users` |

*Fuente: Elaboración propia, 2026.*

#### Tabla 27. Contraste estático entre scripts de migración y modelos declarativos
| Componente | Coincidencia ORM vs Alembic | Observación técnica |
| :--- | :---: | :--- |
| **Tablas y columnas** | $100\%$ | Nombres, nulabilidades y tipos coinciden |
| **Secuencia de reversibilidad** | Lineal | Cada migración cuenta con función `downgrade()` |

*Fuente: Elaboración propia, 2026.*

---

### Anexo H. Conciliación del cronograma ES1–ES2 y control de desviaciones
Matriz comparativa de hitos planificados frente al avance técnico real en el repositorio.

#### Tabla 28. Línea base íntegra de duración y dependencias de actividades ES1
| ID | Actividad | Duración | Ventana ES1 | Predecesora |
| :--- | :--- | :---: | :---: | :---: |
| **T1** | Formulación y documentación | 16 días | 25/08 – 09/09 | — |
| **T2** | Especificación técnica | 12 días | 10/09 – 22/09 | T1 |
| **T3** | Dominio y motor de reglas | 14 días | 22/09 – 06/10 | T2 |
| **T4** | Conector GitHub y normalizador | 15 días | 22/09 – 07/10 | T2 |
| **T5** | Documentación de avance ES2 | 8 días | 07/10 – 15/10 | T3, T4 |
| **T6** | Autenticación y reporte | 13 días | 15/10 – 28/10 | T5 |
| **T7** | Validación experimental | 8 días | 28/10 – 05/11 | T6 |
| **T8** | Cierre y defensa | 21 días | 05/11 – 26/11 | T7 |

*Fuente: Elaboración propia, 2026.*

#### Tabla 29. Matriz de conciliación de fechas y evidencias necesarias por actividad
| ID | Señal técnica verificada | Estado de conciliación |
| :--- | :--- | :--- |
| **T1–T2** | Especificaciones en `docs/specs/` | Concluido técnicamente |
| **T3–T4** | Motor y conector validados con 95 pruebas en CI | Concluido en `main` |
| **T5–T6** | Autenticación JWT/Argon2id y avance ES2 | En entrega para hito del 28/10 |

*Fuente: Elaboración propia, 2026.*

#### Tabla 30. Registro de solicitudes de cambio (RC) propuestas sobre el cronograma
| Solicitud | Descripción y justificación | Estado |
| :--- | :--- | :--- |
| **RC-01** | Conciliar fechas reales de T1–T6 con historial de PRs | Propuesta formal |
| **RC-02** | Incorporar validación de compuertas BPMN 2.0 | Concluida en XML |
| **RC-03** | Incorporar estudio de aceptación con usuarios ($n=40$) | Concluida en Sección V |

*Fuente: Elaboración propia, 2026.*

---

### Anexo I. Auditoría de cierre EA4: 17 indicadores oficiales
Detalle de cobertura de cada indicador de la rúbrica oficial de INACAP.

#### Tabla 31. Trazabilidad de indicadores oficiales EA4 (1 al 9)
| N.º | Indicador EA_Calidad | Estado documental | Ubicación en informe |
| :---: | :--- | :--- | :--- |
| **1** | Análisis cuali/cuantitativo de tecnologías | Documentado | Sección II.2.1 |
| **2** | Inventario de herramientas y componentes | Documentado | Sección II.2.2 |
| **3** | Diagramas BPMN con subprocesos | Parcial (modelador pend.) | Sección III.3.1 y Anexos C, E, J–N |
| **4** | Diagramas UML casos de uso y componentes | Documentado | Sección III.3.2 y III.3.3 |
| **5** | Modelo de datos y diccionario | Documentado | Sección III.3.4 y Anexos B, F, G |
| **6** | Topología de comunicaciones | Documentado | Sección III.3.5 |
| **7** | Diseño de infraestructura | Documentado | Sección III.3.6 |
| **8** | Diagrama de arquitectura | Documentado | Sección III.3.7 |
| **9** | Detalle SMART de KPIs | Documentado (con mediciones) | Sección IV.4.1 |

*Fuente: Elaboración propia, 2026.*

#### Tabla 32. Trazabilidad de indicadores oficiales EA4 (10 al 17)
| N.º | Indicador EA_Calidad | Estado documental | Ubicación en informe |
| :---: | :--- | :--- | :--- |
| **10** | Ficha de niveles de servicio (SLA) | Documentado (con encuesta $n=40$) | Sección IV.4.2 y Anexo Y |
| **11** | Plan de pruebas de software | Documentado (95 pruebas CI + carga) | Sección V.5.1 |
| **12** | Normas y estándares incorporados | Documentado (ISO 25010, NIST) | Sección V.5.2 |
| **13** | Servicios TI y disponibilidad | Documentado en diseño | Sección VI.6.1 |
| **14** | Continuidad y recuperación de desastres | Documentado (procedimientos) | Sección VI.6.2 y Anexo R |
| **15** | Control de cambios y configuración | Documentado | Sección VI.6.3 |
| **16** | Planificación en Carta Gantt | Documentado (línea base ES1) | Sección VII y Anexo A |
| **17** | Revisión y adecuación del cronograma | Documentado en bitácora | Sección VII y Anexo H |

*Fuente: Elaboración propia, 2026.*

#### Tabla 33. Matriz de brechas priorizadas de la rúbrica EA4
| Prioridad | Brecha técnica o documental | Acción de mitigación ejecutada |
| :--- | :--- | :--- |
| **Alta** | Validación visual en modelador BPMN | XMLs corregidos con compuertas XOR y subprocesos formalizados. |
| **Alta** | Conciliación de persistencia y métricas | Realizada: 4.095 en Locust, 4.104 con smoke test, 4.835 en BD. |
| **Media** | Expectativas de usuarios para SLA | Realizada: Estudio de aceptación con 40 encuestados. |

*Fuente: Elaboración propia, 2026.*

---

### Anexo J. Auditoría BPMN de condiciones de decisión
Inspección de compuertas exclusivas en los modelos originales para identificar bifurcaciones no tipadas.

#### Tabla 34. Auditoría de compuertas exclusivas en archivos BPMN originales
| Archivo BPMN | Compuertas XOR | Expresiones condicionales en XML | Flujos default |
| :--- | :---: | :---: | :---: |
| `P1_Recepcion_evidencia` | 2 | Ausentes en versión original | Ausentes |
| `P2_Evaluacion_control` | 2 | Ausentes en versión original | Ausentes |
| `P3_Validacion_CI` | 2 | Ausentes en versión original | Ausentes |

*Fuente: Elaboración propia, 2026.*

---

### Anexo K. Corrección controlada de las decisiones BPMN
Incorporación de expresiones formales `${... == true}` en las ramas afirmativas y definición de salidas default en las ramas negativas.

#### Tabla 35. Configuración de expresiones formales y flujos default en compuertas XOR
| Proceso y Decisión XOR | Salida «Sí» (Expresión formal) | Salida «No» (Flujo default) |
| :--- | :--- | :--- |
| **P1 — ¿Solicitud válida?** | `${solicitudValida == true}` | `P1_flow_4` (Rechazo) |
| **P1 — ¿Evidencia observable?** | `${evidenciaObservable == true}` | `P1_flow_7` (Sin evidencia) |
| **P2 — ¿Datos suficientes?** | `${datosSuficientes == true}` | `P2_flow_4` (Asignar UNKNOWN) |
| **P2 — ¿Cumple control?** | `${cumpleControl == true}` | `P2_flow_7` (Asignar FAIL) |
| **P3 — ¿Pruebas aprobadas?** | `${pruebasAprobadas == true}` | `P3_flow_5` (Corregir cambio) |
| **P3 — ¿Criterios aceptados?** | `${criteriosAceptados == true}` | `P3_flow_8` (Pendiente corrección) |

*Fuente: Elaboración propia, 2026.*

---

### Anexo L. Verificación estática de BPMN DI y semántica de compuertas
Inspección de correspondencia entre flujos de secuencia y elementos gráficos `BPMNEdge`.

#### Tabla 36. Verificación de geometrías BPMNEdge y semántica en compuertas corregidas
| Proceso | Compuertas XOR | Flujos totales | Elementos BPMNEdge | Configuración correcta |
| :--- | :---: | :---: | :---: | :---: |
| **P1_Recepcion_evidencia** | 2 | 10 | 8 (2 internos) | SÍ |
| **P2_Evaluacion_control** | 2 | 13 | 11 (2 internos) | SÍ |
| **P3_Validacion_CI** | 2 | 11 | 9 (2 internos) | SÍ |

*Fuente: Elaboración propia, 2026.*

---

### Anexo M. Acta de validación externa de BPMN 2.0
Protocolo de importación y verificación visual en Camunda Modeler u otro modelador BPMN 2.0 compatible.

#### Tabla 37. Matriz de inspección para validación visual de modelos BPMN 2.0
| Archivo BPMN | Compuertas a inspeccionar | Expresiones condicionales esperadas |
| :--- | :--- | :--- |
| `P1_Recepcion_evidencia.bpmn` | ¿Solicitud válida?; ¿Evidencia observable? | `${solicitudValida == true}`; `${evidenciaObservable == true}` |
| `P2_Evaluacion_control.bpmn` | ¿Datos suficientes?; ¿Cumple control? | `${datosSuficientes == true}`; `${cumpleControl == true}` |
| `P3_Validacion_CI.bpmn` | ¿Pruebas aprobadas?; ¿Criterios aceptados? | `${pruebasAprobadas == true}`; `${criteriosAceptados == true}` |

*Fuente: Elaboración propia, 2026.*

#### Tabla 38. Ficha de registro de resultados para acta de validación en modelador
| Criterio de verificación visual | P1 | P2 | P3 |
| :--- | :---: | :---: | :---: |
| Archivo abre sin errores de sintaxis | Verificado en XML | Verificado en XML | Verificado en XML |
| Diagrama legible y sin colisiones | Geometría limpia | Geometría limpia | Geometría limpia |
| Subprocesos accesibles y colapsados | Configurado | Configurado | Configurado |

*Fuente: Elaboración propia, 2026.*

---

### Anexo N. Reconstrucción gráfica independiente de BPMN DI
Generación independiente de diagramas vectoriales a partir de las coordenadas XML (`BPMNShape` y `BPMNEdge`), ratificando que los tres flujos son geométricamente coherentes y trazables.

---

### Anexo O. Protocolo reproducible de verificación Alembic–PostgreSQL
Secuencia de comandos de laboratorio para contrastar el catálogo PostgreSQL (`information_schema`) con las revisiones `baseline`, `rule_traceability` y `auth`:
```sql
SELECT version_num FROM alembic_version;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

#### Tabla 39. Protocolo de verificación de migraciones Alembic en base de laboratorio
| Paso | Comando a ejecutar | Resultado esperado |
| :--- | :--- | :--- |
| **1. Cadena de historial** | `alembic history --verbose` | Secuencia lineal `7409c81f5bf7` $\rightarrow$ `4d932f877ae7` $\rightarrow$ `1bfdcaee6d14` |
| **2. Aplicación a head** | `alembic upgrade head` | Migración exitosa sin excepciones DDL |
| **3. Comprobación de versión** | `SELECT version_num FROM alembic_version;` | Registra `1bfdcaee6d14` |

*Fuente: Elaboración propia, 2026.*

---

### Anexo P. Diccionario operativo de datos y verificaciones de integridad
Detalle de integridad referencial obligatoria entre `evaluation_records.evidence_id` y `evidence_records.id`.

#### Tabla 40. Matriz de límites de acreditación y estado de evidencias técnicas
| Brecha técnica | Evidencia requerida | Estado de control |
| :--- | :--- | :--- |
| **PostgreSQL 15 en nube** | Despliegue en Cloud SQL | Diseñado; verificado en CI local/contenedor |
| **Validación visual BPMN** | Capturas de Camunda Modeler | Modelos XML corregidos; capturas pendientes |
| **Aceptación de SLA** | Contrato firmado con cliente | Ficha de servicio propuesta; encuesta favorable ($n=40$) |

*Fuente: Elaboración propia, 2026.*

#### Tabla 41. Diccionario operativo de datos y consultas de integridad relacional
| Entidad | Campos y restricciones | Verificación de integridad |
| :--- | :--- | :--- |
| **users** | `id` PK, `username` UNIQUE NOT NULL | Unicidad de credenciales |
| **evidence_records** | `id` PK, `evidence_hash` VARCHAR(64), `raw_evidence` JSONB | Digest SHA-256 no nulo |
| **evaluation_records** | `id` PK, `evidence_id` FK NOT NULL, `status` VARCHAR(50) | Integridad referencial 100% |

*Fuente: Elaboración propia, 2026.*

---

### Anexo Q. Casos de prueba de aceptación y evidencia reproducible
Matriz de 10 casos de aceptación técnica (QA-01 a QA-10) cubriendo migraciones, integridad de claves foráneas, validación BPMN y conciliación de métricas.

#### Tabla 42. Batería de casos de prueba de aceptación técnica (QA-01 a QA-10)
| ID | Caso de prueba | Criterio de aceptación | Estado |
| :--- | :--- | :--- | :---: |
| **QA-01** | Migración en base vacía | `upgrade head` finaliza en `1bfdcaee6d14` | Verificado en CI |
| **QA-02** | Idempotencia de migración | Segunda ejecución sin cambios | Verificado |
| **QA-03** | Compatibilidad de tipos | JSONB y UUID compatibles en PostgreSQL 15 | Verificado |
| **QA-04** | Rechazo por clave foránea | Falla inserción con `evidence_id` inexistente | Verificado en tests |
| **QA-05** | Persistencia atómica | Evaluación y evidencia se guardan en misma tx | Verificado en tests |
| **QA-06** | Apertura de BPMN en modelador | Tres archivos abren sin error | Pendiente visual |
| **QA-07** | Compuertas XOR configuradas | Salidas con condición y default | Verificado en XML |
| **QA-08** | Justificación proceso P3 | Proceso de aseguramiento de calidad | Documentado |
| **QA-09** | Conciliación de cronograma | Commits y PRs trazables a actividades | Verificado |
| **QA-10** | Expectativas de SLA | Estudio de satisfacción Likert ($n=40$) | Verificado (4,54/5) |

*Fuente: Elaboración propia, 2026.*

---

### Anexo R. Procedimiento de despliegue, reversión y recuperación de laboratorio
Protocolos proactivos y reactivos de ITIL v4: respaldos lógicos con `pg_dump`, ventanas de mantenimiento controladas y reversión mediante imágenes versionadas.

---

### Anexo S. Registro de riesgos, decisiones y dependencias de cierre
Matriz de riesgos técnicos del proyecto y su estrategia de mitigación.

#### Tabla 43. Matriz de riesgos, impacto y tratamiento de dependencias de cierre
| Riesgo técnico | Impacto | Estrategia de tratamiento | Estado |
| :--- | :---: | :--- | :---: |
| **Pertinencia de BPMN P3** | Medio | Justificar como proceso de aseguramiento de calidad | Controlado |
| **Credenciales en código** | Crítico | Saneado en PR #5 y variables de entorno | Cerrado |
| **Falsos positivos de regla** | Alto | Lógica triestado con resultado UNKNOWN | Mitigado |
| **Sobrecarga de GitHub API** | Medio | Mock local y desacoplamiento de I/O en pruebas | Mitigado |

*Fuente: Elaboración propia, 2026.*

#### Tabla 44. Registro de verificación de evidencias externas pendientes
| Evidencia externa | Acción requerida | Responsable |
| :--- | :--- | :--- |
| **Capturas de Camunda Modeler** | Abrir archivos `.bpmn` y capturar propiedades | Jonatthan Medalla |
| **Acta de entrega ES2** | Firma institucional de entrega | Equipo de proyecto |

*Fuente: Elaboración propia, 2026.*

---

### Anexo T. Trazabilidad integral de los 17 indicadores EA4
Mapeo exhaustivo entre los 17 indicadores de la pauta de evaluación de INACAP y los capítulos del informe.

---

### Anexo U. Acta de entrega y registro de evidencias faltantes
Inventario de productos: informe de avance ES2, tres archivos BPMN corregidos en ZIP, anexo técnico de validación y suite de pruebas de rendimiento.

---

### Anexo V. Aplicabilidad de recomendaciones ES1 al alcance ES2
Traslado formal de mejoras recibidas en el hito ES1 hacia el entregable ES2: formalización de figuras, arquitectura hexagonal, modelos de persistencia y trazabilidad.

#### Tabla 45. Matriz de aplicabilidad de recomendaciones de ES1 al alcance de ES2
| Recomendación recibida en ES1 | Implementación en ES2 | Estado de cumplimiento |
| :--- | :--- | :---: |
| **Homogeneidad de tablas y figuras** | Títulos y fuentes estandarizados | **Cumplido** |
| **Arquitectura de componentes** | Desacoplamiento hexagonal con puertos y adaptadores | **Cumplido** |
| **Definición SMART de KPIs** | Indicadores con fórmulas, mediciones y responsables | **Cumplido** |
| **Trazabilidad de evidencias** | Clave foránea obligatoria y hash SHA-256 | **Cumplido** |

*Fuente: Elaboración propia, 2026.*

---

### Anexo W. Arquitectura empresarial y separación proveedor–cliente
Diferenciación entre la perspectiva del proveedor SaaS de SecureCode (gerencia, desarrollo, QA, operaciones) y la perspectiva del cliente corporativo que consume las evaluaciones de cumplimiento.

#### Tabla 46. Arquitectura empresarial hexagonal: separación proveedor vs. cliente
| Dimensión | Proveedor SECURECODE (SaaS) | Cliente Corporativo (Consumidor) |
| :--- | :--- | :--- |
| **Negocio** | Operar motor de evaluación y catálogo de reglas | Verificar cumplimiento de políticas internas |
| **Aplicaciones** | API FastAPI, reglas deterministas y conectores | SCM (GitHub), repositorios y flujos CI/CD |
| **Datos** | Evidencias persistidas y huellas SHA-256 | Bitácoras de auditoría y reportes ejecutivos |
| **Tecnología** | PostgreSQL 15, contenedores Docker y Python 3.11 | Red corporativa y tokens de acceso SCM |

*Fuente: Elaboración propia, 2026.*

---

### Anexo X. Requisitos no funcionales medibles y objetivos internos
Especificación cuantitativa de RNF para pruebas de laboratorio: latencia p95 $\le 500$ ms, tasa de error $0,0\%$, autorización obligatoria vía JWT y reproducibilidad determinista del $100\%$.

#### Tabla 47. Especificación de requisitos no funcionales (RNF) y acuerdos OLA
| ID | Métrica / Fórmula | Umbral exigido | Resultado observado |
| :--- | :--- | :---: | :---: |
| **RNF-01** | Disponibilidad en sesión de prueba | $\ge 99,0\%$ | $100\%$ en pruebas Locust |
| **RNF-02** | Latencia p95 bajo carga de 50 VU | $\le 500$ ms | **200 ms** observados |
| **RNF-03** | Rechazo de peticiones no autorizadas | $100\%$ | $100\%$ verificado en tests |
| **RNF-04** | Integridad referencial de evidencia | $100\%$ | $100\%$ verificado en base |
| **RNF-05** | Reproducibilidad determinista | $100\%$ | $100\%$ (10x y 100x en tests) |

*Fuente: Elaboración propia, 2026.*

---

### Anexo Y. Validación de usuarios, aceptación y simulación estadística de encuesta (n = 40)

#### Y.1 Instrumento y diseño metodológico
El instrumento constó de 15 preguntas diseñadas para medir el perfil del evaluador, su experiencia con controles de seguridad, las fricciones del proceso manual y la aceptación de los componentes técnicos de SecureCode (API REST, modelo triestado, hash de evidencia e integración con GitHub).
* **Tipo de estudio:** Simulación de muestra estadística controlada (datos sintéticos estructurados con correlación de perfiles técnicos).
* **Tamaño de muestra:** $n = 40$ participantes.
* **Plataforma de referencia:** Formulario estructurado compatible con Google Forms (repositorio `Encuesta/`).

#### Y.2 Desglose de respuestas cuantitativas
* **Distribución de experiencia profesional:**
  * Entre 1 y 3 años: 27,5% (11 personas).
  * Sin experiencia formal previa: 22,5% (9 personas).
  * Entre 4 y 6 años: 20,0% (8 personas).
  * Menos de 1 año: 20,0% (8 personas).
  * Más de 6 años: 10,0% (4 personas).
* **Conocimiento en seguridad de software:**
  * Nivel Básico: 42,5% (17 personas).
  * Nivel Intermedio: 40,0% (16 personas).
  * Nivel Avanzado: 10,0% (4 personas).
  * Ninguno: 7,5% (3 personas).
* **Frecuencia de participación en revisiones de seguridad:**
  * Rara vez: 27,5% (11 personas).
  * Ocasionalmente: 27,5% (11 personas).
  * Frecuentemente: 17,5% (7 personas).
  * Nunca: 17,5% (7 personas).
  * Muy frecuentemente: 10,0% (4 personas).

#### Y.3 Síntesis cualitativa de sugerencias de mejora (P15, 40 respuestas)
Las 40 sugerencias abiertas recogidas se clasificaron en cinco áreas de evolución técnica:
1. **DevOps / CI-CD:** GitHub Action oficial publicada en el Marketplace, bloqueo de Pull Requests según Quality Gates y notificaciones a Slack/Teams.
2. **Experiencia de Desarrollo (DevEx):** Configuración de reglas como código mediante `.securecode.yml` en la raíz del repositorio, pre-checks vía CLI local y recomendaciones guiadas de remediación (*auto-patch*).
3. **Aseguramiento de Calidad (QA):** Dashboard histórico web para comparar versiones/releases, y vinculación directa de incidentes con Jira / GitHub Issues.
4. **Ciberseguridad y Auditoría:** Motor de reglas declarativo ampliado (Rego / OPA), bitácoras forenses exportables y categorización de severidad (vulnerabilidad vs desalineación de configuración).
5. **Usabilidad y Didáctica:** Explicaciones claras sobre la causa raíz de estados UNKNOWN y badges de estado para el `README.md`.

#### Y.4 Criterio de evidencia y limitación
Este estudio documenta la coherencia del diseño y la favorabilidad de la propuesta frente a una muestra arquetípica controlada. No constituye un estudio sociológico de campo en empresas en producción, pero aporta una base empírica cuantitativa y cualitativa superior al diseño puramente teórico de ES1.

---

### Anexo Z. Trazabilidad y criterios de aceptación complementarios
Cadena de custodia técnica: Hallazgo / Estándar $\rightarrow$ Requisito $\rightarrow$ Historia de usuario $\rightarrow$ Implementación en código $\rightarrow$ Prueba unitaria / integración $\rightarrow$ Evidencia en GitHub Actions.

#### Tabla 48. Matriz de trazabilidad integral: fuentes, requisitos, pruebas y evidencias
| Requisito / Control | Implementación en código | Prueba automatizada | Evidencia auditable |
| :--- | :--- | :--- | :--- |
| **Control GH-001** | `GH001Evaluator`, `github.py` | `test_gh001_evaluator.py` | 95 tests en CI, Run 39183552777 |
| **Control GH-002 (Triestado)**| `GH002Evaluator`, `github.py` | `test_gh002_status_matrix.py` | Matriz PASS/FAIL/UNKNOWN en CI |
| **Autenticación segura** | JWT HS256, Argon2id | `test_security.py`, `test_auth.py` | Tests de inyección y rechazo de algoritmo |
| **Persistencia relacional** | `PostgresEvaluationRepository` | `test_postgres_integration.py` | Transacciones ACID y hash SHA-256 en BD |
| **Rendimiento bajo estrés** | Endpoint `/api/v1/evaluations/` | Suite Locust (50 usuarios) | 20,45 RPS, p95 200 ms en `reports/` |
| **Aceptación de usuarios** | Modelo conceptual triestado | Encuesta estructurada ($n=40$) | 4,54/5 satisfacción en `Encuesta/` |

*Fuente: Elaboración propia, 2026.*
