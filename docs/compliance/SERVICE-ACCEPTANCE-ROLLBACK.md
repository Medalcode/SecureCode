# Reversión — aceptación de documentos de servicio

## Revisión

- ID: `f2b6c8d0a913`
- Anterior: `e7b1c4d2a809`
- Tabla creada: `service_document_acceptances`
- Índices creados:
  - `ix_service_document_acceptances_org_accepted_at`
  - `ix_service_document_acceptances_user_accepted_at`

## Contenido

La migración agrega un historial append-only de aceptaciones realizadas por el propietario de una organización. Cada fila conserva organización, usuario, paquete documental, documento individual, versión, huella SHA-256, ruta pública, tipo de aceptación y marca UTC. No modifica cuentas, roles, organizaciones, membresías, reglas ni resultados de evaluación.

## Reversión controlada

Antes de ejecutar cualquier cambio en un entorno compartido se debe exportar el esquema y las filas de `service_document_acceptances`. La reversión elimina únicamente la tabla y sus índices:

```bash
python -m alembic downgrade e7b1c4d2a809
```

No se debe aplicar una reversión en producción sin una ventana de cambio y una copia de seguridad verificable.

## Verificación posterior

1. `python -m alembic current` debe informar `e7b1c4d2a809`.
2. La tabla `service_document_acceptances` no debe existir.
3. Las tablas de usuarios, organizaciones, membresías y evaluaciones deben conservar sus filas.
4. La aplicación con el código anterior debe iniciar y responder las rutas públicas y de autenticación.

## Reaplicación

```bash
python -m alembic upgrade f2b6c8d0a913
```

La reaplicación crea una tabla vacía. El historial borrado no se reconstruye automáticamente; debe restaurarse desde la copia de seguridad si la auditoría lo requiere.
