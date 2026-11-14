# P1 — prueba local concurrente de 100 usuarios virtuales

## Identificación

- Fecha de captura (UTC): 2026-11-14T02:59:17Z.
- Commit evaluado: `5f070e86e434a5ea048a0599abfce48a84232dc9`.
- Entorno: Windows local del proyecto, PostgreSQL local `securecode_test`.
- API bajo prueba: `http://127.0.0.1:8000`.
- Fuente GitHub simulada: `http://127.0.0.1:8001`.
- Herramienta: Locust, ejecutada mediante `scripts/run_local_load_test.ps1`.
- Configuración solicitada: 100 usuarios virtuales, incorporación de 10 usuarios/s y
  duración de 2 minutos.

## Alcance y aislamiento

El script sólo acepta la base local `securecode_test` y puertos loopback. Inició
la API y el simulador GitHub localmente y los detuvo al finalizar. No consultó
GitHub real, Cloud Run, Supabase, Neon ni servicios de facturación.

## Resultado verificable

El proceso Locust terminó con código `0`. Los artefactos versionados de la
ejecución están en `reports/load-2026-11-13-235713/`.

| Métrica del CSV final | Valor |
| --- | ---: |
| Solicitudes agregadas | 6.160 |
| Fallos | 0 (0,00 %) |
| Rendimiento agregado | 51,77 solicitudes/s |
| Latencia media agregada | 388,93 ms |
| Mediana agregada | 390 ms |
| P95 agregado | 680 ms |
| P99 agregado | 930 ms |
| Máximo observado | 2.122,34 ms |

Desglose de evaluaciones: GH-001 = 1.854, GH-002 = 1.775 y GH-003 = 1.803;
además se registraron 100 autenticaciones y 628 comprobaciones de salud. Los
CSV de fallos y excepciones contienen únicamente sus cabeceras, sin filas de
errores.

## Interpretación responsable

Esta es una evidencia reproducible de carga **local y simulada**. No acredita
SLA, capacidad de producción, latencia de GitHub real, desempeño de Cloud Run
ni costos cloud. El valor de consola de 6.183 mostrado durante la detención no
coincidió con el total persistido de 6.160; para toda conclusión se adopta el
CSV final versionado como fuente de verdad.
