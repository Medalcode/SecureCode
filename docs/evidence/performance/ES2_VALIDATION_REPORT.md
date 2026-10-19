# Informe de Validación Final (ES2)

## 1. Verificación de Métricas (Consistencia Documental)
He auditado exhaustivamente los archivos `.csv` generados en la carpeta `reports/` frente a los datos publicados en `ES2_PERFORMANCE_RESULTS.md`:
* **RPS (Throughput)**: El valor reportado para el escenario de Estrés (20.45 req/s) corresponde **estrictamente** al endpoint `POST /api/v1/evaluations/gh-001` y no se mezcló con los 9.12 req/s del endpoint `/health` (Aggregated totalizó 30.0 req/s).
* **VUsers en Estrés**: Los registros de Locust (p. ej. `stress_load_stats_history.csv`) demuestran que, tras los 10 segundos iniciales de ramp-up (5/s), el sistema sostuvo exactamente 50 usuarios virtuales durante el resto de los 2 minutos, tal como se instruyó.

## 2. Aislamiento de Red Externa
He inspeccionado el parche `scripts/run_perf_api.py` y el adaptador `github.py`. 
* **Hallazgo**: `urllib.request` fue interceptado globalmente mediante un parche de ejecución. Cualquier objeto `urllib.request.Request` cuya URL empiece con `https://api.github.com` se reescribe determinísticamente hacia `127.0.0.1:8001` antes de abrir el socket de red. Esto asegura que todo el tráfico de evaluación de las pruebas permanezca confinado al servidor mock local y no consuma cuota ni dependa de la API productiva de GitHub.

## 3. Verificación de Latencia y Distribución
* **Ajuste de Percentiles**: La latencia media de GH-001 bajo estrés fue de 172ms, con una mediana de 160ms y un percentil 95 de **200ms** (el percentil 98 alcanzó 300ms).
* **Análisis de Overhead**: Dado que el Mock inyecta **150ms** de latencia artificial en `/branches/{branch}/protection`, la sobrecarga atribuible al procesamiento interno (FastAPI, serialización Pydantic y persistencia síncrona en PostgreSQL) fue de apenas ~10ms en la mediana y ~50ms en el p95 bajo una carga de 50 usuarios concurrentes.

## 4. Persistencia de PostgreSQL y Conciliación de Métricas
* **Verificación**: 
  * Los 5 escenarios formales de Locust generaron exactamente **4.095 peticiones** HTTP 200 en `POST /api/v1/evaluations/gh-001` (262 nominal + 228 prog10 + 497 prog20 + 676 prog30 + 2.432 estrés).
  * Al incluir las 9 solicitudes del Smoke Test inicial, el total acumulado de la sesión de Locust fue de **4.104 evaluaciones**.
  * El recuento total `SELECT COUNT(*)` sobre la tabla `evaluation_records` arrojó **4.835 registros**, los cuales concilian perfectamente al considerar los 731 registros preexistentes de las ejecuciones de prueba unitarias e integradas previas.
  * La persistencia se verificó no solo por el código HTTP 200, sino mediante consultas directas a la base de datos confirmando integridad referencial entre `evaluation_records` y `evidence_records`.

## Conclusión
La evidencia alojada en `ES2_PERFORMANCE_RESULTS.md` ha sido filtrada, corregida en sus percentiles y contrastada exitosamente contra el código base y la base de datos real. Todas las cifras documentadas están respaldadas por los reportes CSV y la base de datos, siendo aptas y rigurosas para su incorporación en la entrega del informe ES2.
