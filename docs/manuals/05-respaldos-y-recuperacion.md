# Runbook de respaldos y recuperación — SecureCode

## 1. Alcance y estado real

Este runbook describe el procedimiento propio de SecureCode para bases PostgreSQL y el estado verificado de la integración con Supabase. No habilita trabajos programados, no crea recursos cloud y no accede a producción.

- Supabase documenta respaldos diarios automáticos para planes Pro (7 días), Team (14 días) y Enterprise (30 días). El plan Free no permite descargar respaldos; se recomienda exportación propia con Supabase CLI.
- Point-in-Time Recovery (PITR) es un add-on de planes pagados. La documentación de Supabase indica un RPO máximo de dos minutos en el peor caso y advierte que al activarlo se sustituyen los respaldos diarios.
- Los respaldos de Supabase cubren la base de datos; los objetos de Storage no se restauran con ellos. Las contraseñas de roles personalizados tampoco se incluyen en descargas de respaldos diarios.
- La cobertura contratada del proyecto, la retención real y la activación de PITR deben confirmarse en el panel del proveedor antes de depender de ellas. Este repositorio no contiene evidencia de esa configuración.

## 2. Objetivos propuestos (no contractuales)

| Escenario | Objetivo propuesto | Base de la propuesta | Estado |
|---|---|---|---|
| Pérdida lógica con respaldo diario del proveedor | RPO < 24 h | Respaldos diarios documentados por Supabase en planes pagados |No garantizado|
| Pérdida lógica con PITR habilitado | RPO <= 2 min | Documentación oficial de Supabase sobre WAL cada dos minutos |Requiere add-on y confirmación|
| Recuperación de cómputo | RTO < 15 min | Valor técnico ya publicado por `/api/v1/system/overview` |No incluye restauración de datos|
| Restauración de base pequeña en entorno aislado | RTO objetivo < 60 min | Verificación local con dataset sintético |Solo entorno de prueba|
| Retención local de artifacts | 30 días | Política propuesta de menor privilegio y rotación |Pendiente de automatización|

Estos valores son metas técnicas de diseño. Un tiempo medido en el dataset sintético no permite prometer el tiempo de restauración de producción.

## 3. Modelo de seguridad

- Los scripts solo aceptan entornos explícitamente declarados como `test`.
- La conexión se entrega únicamente por variables de entorno: `BACKUP_SOURCE_DATABASE_URL` para origen y `RESTORE_TARGET_DATABASE_URL` para el servidor de destino.
- No se aceptan contraseñas como argumentos de línea de comandos ni se escriben en manifiestos, evidencia, logs o nombres de archivo.
- Las URLs de origen y destino deben usar host loopback. Los nombres de base de origen y destino deben estar en listas de permitidos o seguir los prefijos aislados `securecode_backup_source_*` y `securecode_restore_*`.
- La restauración exige confirmación literal `RESTORE_TO_ISOLATED_TEST_DATABASE`, crea una base nueva y nunca sobrescribe una existente.
- Los artifacts se excluyen de Git mediante `.gitignore` y se crean con permisos restringidos cuando el sistema de archivos lo permite.
- El manifiesto incluye SHA-256, tamaño, versión del servidor, herramientas, head de Alembic, huellas por tabla y validación de integridad referencial; no incluye cadenas de conexión.

## 4. Respaldo manual validado

1. Obtener la URL de la base de pruebas desde el gestor de secretos y exportarla como `BACKUP_SOURCE_DATABASE_URL`. No pegarla en comandos ni documentos.
2. Verificar que `pg_dump` esté disponible. Si no está en `PATH`, exportar `PG_BIN_DIR` con la carpeta de binarios de PostgreSQL.
3. Ejecutar:

```powershell
python scripts\backup_postgres.py create --allowed-database securecode_backup_source_<id> --output-dir backups
```

4. Confirmar en la salida: `status=ok`, ruta del artifact, manifiesto `.backup.manifest.json`, `sha256`, `alembic_head=d4e9f1a2b3c4` y `tables=17`.
5. Verificar de forma independiente:

```powershell
python scripts\backup_postgres.py verify --backup backups\<archivo>.backup --manifest backups\<archivo>.backup.manifest.json
```

Si el tamaño, el SHA-256, el esquema del manifiesto o las huellas no coinciden, el comando falla y el artifact no debe usarse para restauración.

## 5. Restauración aislada validada

1. Exportar `RESTORE_TARGET_DATABASE_URL` hacia una base de mantenimiento del mismo clúster de pruebas (`postgres` o `*_test`), obtenida del gestor de secretos.
2. Ejecutar:

```powershell
python scripts\restore_postgres.py --backup backups\<archivo>.backup --manifest backups\<archivo>.backup.manifest.json --confirm RESTORE_TO_ISOLATED_TEST_DATABASE
```

3. El script crea una base `securecode_restore_*`, aplica `pg_restore` en una sola transacción y valida:
   - SHA-256 y manifiesto del artifact.
   - Head de Alembic del destino.
   - Conteo y huella SHA-256 de las 17 tablas de datos.
   - Todas las foreign keys, sin filas huérfanas.
4. Si falla, no elimina la base creada: se conserva para diagnóstico. Cualquier eliminación posterior requiere autorización explícita y verificación del nombre.
5. La restauración sobre producción no está implementada. Debe realizarse mediante el procedimiento del proveedor, en una Instancia/proyecto nuevo o ventana de indisponibilidad autorizada, con roles y secretos reconfigurados después.

## 6. Verificación integral reproducible

El orquestador crea una base sintética nueva, aplica migraciones, siembra dos organizaciones con owners, analysts, autorizaciones, evaluaciones GH-001/GH-002/GH-003, evidencias, aceptaciones de documentos, auditoría, sesiones, trial y cuotas, genera el respaldo y lo restaura en otra base nueva.

Requisitos previos:

- `RESTORE_TARGET_DATABASE_URL` exportado desde el gestor de secretos.
- `pg_dump` y `pg_restore` disponibles en `PATH` o `PG_BIN_DIR`.
- Clúster PostgreSQL local de pruebas, sin acceso a producción.

Comando:

```powershell
python scripts\verify_backup_restore.py --output-dir artifacts\backup-verification --evidence-file artifacts\backup-verification\evidence.json
```

La evidencia JSON debe registrar `status=ok`, bases distintas, conteos iguales entre origen y destino, dos organizaciones, seis evaluaciones, cuatro aceptaciones, dos sesiones, 17 tablas verificadas y foreign keys revisadas. Ningún secreto debe aparecer en la salida.

También puede ejecutarse la prueba automatizada aislada:

```powershell
pytest -q tests/integration/test_backup_restore.py -m postgres
```

## 7. Automatización propuesta (no activada)

| Capa | Propuesta | Estado |
|---|---|---|
| Programación | Cloud Scheduler diario 03:00 UTC apuntando a Cloud Run Job `securecode-backup` |Diseño, no creado|
| Ejecución | Cloud Run Job con imagen de SecureCode, sin tráfico público y service account dedicada |Diseño, no creado|
| Secretos | Secret Manager como única fuente de la URL; inyección por variable de entorno en el job |Diseño, no creado|
| Almacenamiento | Bucket GCS con versionado, retención 30 días, CMEK, acceso restringido y registro de auditoría |Diseño, no creado|
| Observabilidad | Alerta si falla el job, falta el manifiesto, cambia el head de Alembic o no hay respaldo reciente |Diseño, no creado|
| Proveedor | Evaluar PITR de Supabase si se requiere RPO <= 2 min; confirmar plan, costo y retención antes de activarlo |Pendiente de decisión|

## 8. Incidentes y responsabilidades

| Situación | Acción inmediata | Responsable |
|---|---|---|
| Respaldo corrupto o manifiesto inválido | Marcar artifact como no usable, conservarlo y ejecutar nuevo respaldo; no restaurar |Platform owner|
| Head de Alembic distinto | Detener restauración; revisar migraciones y versión de la imagen |DBA/Platform owner|
| Huellas o conteos distintos | Conservar base, comparar con evidencia y escalar; no promover la base |DBA on-call|
| Violación de integridad referencial | Conservar base, revisar transacción parcial y repetir desde artifact verificado |DBA on-call|
| Intento de restauración a producción | Rechazar; requerir autorización, proyecto nuevo y procedimiento del proveedor |Platform owner + dueño del servicio|
| Pérdida superior al RPO propuesto | Declarar incidente; evaluar PITR del proveedor y brecha de cobertura del plan |Dueño del servicio|

## 9. Estado de verificación en esta entrega

- Respaldo, verificación y restauración ejecutados contra PostgreSQL aislado con datos sintéticos.
- Sin conexión a producción, sin credenciales productivas y sin creación de recursos cloud.
- Sin trabajos programados activados.
- La cobertura de Supabase y la programación real quedan **pendientes de validación operativa**.
