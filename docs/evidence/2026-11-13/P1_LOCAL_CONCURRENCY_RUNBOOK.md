# P1 — Ejecución local de concurrencia

El script `scripts/run_local_load_test.ps1` ejecuta una prueba Locust aislada
sin requerir tres terminales. Antes de iniciar, exige que los puertos locales
8000 y 8001 estén libres. Solicita la contraseña PostgreSQL local una vez,
construye una conexión sólo hacia `securecode_test`, inicia el simulador
GitHub en loopback y la API local, y detiene ambos procesos al terminar.

Ejemplo para 100 usuarios virtuales durante dos minutos:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_local_load_test.ps1 `
  -Users 100 -SpawnRate 10 -Duration 2m
```

El reporte queda en `reports/load-<fecha-hora>/` e incluye CSV de Locust,
logs de API/mock y `run-metadata.json`. La prueba no permite usar GitHub real,
Supabase, Neon, Cloud Run ni otra base de datos.

Los resultados sólo describen concurrencia en el equipo local y en el
simulador. No constituyen un SLA, una medición de producción ni una factura.
