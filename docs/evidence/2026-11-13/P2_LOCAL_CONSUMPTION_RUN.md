# P2 — Ejecución local de consumo y rendimiento

## Identificación

| Campo | Valor |
|---|---|
| Fecha de captura (UTC) | 2026-11-14T01:55:35.835497+00:00 |
| Commit evaluado | `406f2d5e65f904e726fd198d9fcedf6ddfa7097f` |
| Plataforma | Windows 10 `10.0.19045-SP0` |
| Python | 3.14.6 |
| Base de datos | PostgreSQL local `securecode_test` |
| Transporte de evidencia | Simulador GitHub local `127.0.0.1:8001` |

## Alcance y reproducibilidad

La ejecución se hizo contra una API local en `127.0.0.1:8000`, con el modo de
prueba de GitHub limitado al simulador loopback. No se utilizó GitHub real,
Supabase, Neon, Cloud Run ni una credencial de producción.

El recolector se ejecutó con:

```powershell
python scripts\measure_local_performance.py `
  --api-pid <PID_API_LOCAL> `
  --output-dir reports\2026-11-13-local-full
```

Los artefactos fuente son:

- `reports/2026-11-13-local-full/observations.csv`
- `reports/2026-11-13-local-full/summary.json`

## Resultado observado

| Métrica | Resultado |
|---|---:|
| Controles | GH-001, GH-002, GH-003 |
| Perfiles del simulador | small, medium, large |
| Evaluaciones por combinación | 100 |
| Observaciones totales | 900 |
| Observaciones exitosas | 900 |
| Errores | 0 |
| Latencia P95 agregada | 419.0112 ms |
| Solicitudes al simulador | 2,400 |
| Tamaño `evaluation_records` | 32,768 B → 237,568 B |
| Tamaño `evidence_records` | 32,768 B → 270,336 B |
| CPU API, usuario | 1.40625 s → 17.328125 s |
| CPU API, sistema | 0.421875 s → 6.4375 s |
| RSS API | 99,254,272 B → 104,681,472 B |

Las 2,400 solicitudes al simulador coinciden con la topología esperada: por
cada perfil, GH-001 realiza tres consultas, GH-002 tres y GH-003 dos; para 100
evaluaciones y tres perfiles: `(3 + 3 + 2) × 100 × 3 = 2,400`.

## Límites de interpretación

Los perfiles `small`, `medium` y `large` aplican latencias deterministas de
10, 50 y 100 ms en el simulador. Por ello esta evidencia demuestra el flujo
local aislado y el consumo relativo de la aplicación, pero **no** demuestra
latencia de GitHub, capacidad de Cloud Run, costos de GCP/Supabase ni un SLA de
producción. No se han calculado montos ni se han modificado supuestos
financieros.
