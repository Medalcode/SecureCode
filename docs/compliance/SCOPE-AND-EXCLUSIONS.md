# Alcance técnico y exclusiones de la Fase 1

## Alcance incluido

Esta Fase 1 se limita a la trazabilidad normativa documental de GH-001, GH-002 y GH-003 frente a NIST SP 800-53 Rev. 5 y SP 800-53A Rev. 5.

Se incluye:

- Revisión de los JSON canónicos en `src/securecode/rules/`.
- Revisión de `get_rules_directory()`, `get_rule_definition()`, `evaluate_rule()` y los evaluadores `evaluate_gh001`, `evaluate_gh002` y `evaluate_gh003`.
- Revisión de los modelos de evidencia `GH001Evidence`, `GH002Evidence` y `GH003Evidence`.
- Revisión del adaptador GitHub y de las pruebas unitarias, API y de integración simulada existentes.
- Validación documental de correspondencias con `CM-3`, `CM-3(1)`, `CM-5`, `CM-5(1)`, `CM-5(4)`, `CM-14`, `SI-7`, `SI-7(1)` y `SI-7(6)`.
- Creación de la matriz de trazabilidad, las fichas técnicas y este documento de alcance.
- Creación de pruebas automáticas que verifican que la documentación no se desincronice de las reglas canónicas.

## Fuentes de verdad

| Elemento | Fuente de verdad | Observación |
|---|---|---|
| Condiciones y umbrales | `src/securecode/rules/GH-*.json` | Los evaluadores consumen estos archivos. |
| Carga de reglas | `src/securecode/engine/evaluator.py` | `SECURECODE_RULES_DIR` puede sustituir el directorio en runtime. |
| Semántica de estado | `src/securecode/engine/executor.py` y `src/securecode/engine/types.py` | `PASS`, `FAIL`, `UNKNOWN`; `FAIL` prevalece en `AND`. |
| Evidencia GitHub | `src/securecode/adapters/github.py` y modelos `GH00*Evidence` | Define rutas API y transformación de respuestas. |
| Normativa NIST | Publicaciones oficiales NIST SP 800-53 Rev. 5 y SP 800-53A Rev. 5 | Las correspondencias parciales son el único modo válido de relación; cada una se declara como parcial y no implica certificación. |

`rules/` en la raíz contiene copias JSON-equivalentes de las reglas, pero no se introduce un catálogo normativo paralelo. Si las copias divergen, prevalece el directorio canónico cargado por el motor.

## Exclusiones de implementación

No se realizan ni se requieren para esta Fase 1:

- Cambios en el motor, umbrales, operadores o semántica de `PASS`, `FAIL` y `UNKNOWN`.
- Cambios en autenticación, autorización, roles, sesiones, contraseñas o JWT.
- Migraciones de base de datos o cambios de esquema.
- Cambios en dependencias, infraestructura, despliegues o configuración de producción.
- Modificación de la portada pública, catálogo visual, flujo de registro, términos comerciales o contratación.
- Generación de credenciales, uso de secretos o llamadas a GitHub reales con tokens.
- Commits, push, merge, creación de PR o despliegue.
- Declaraciones de certificación, autorización o cumplimiento pleno de NIST.

## Exclusiones normativas

SecureCode no sustituye una evaluación completa de SP 800-53A. En particular, no realiza entrevistas, no revisa políticas organizacionales completas, no valida evidencia de personal, no emite findings formales ni construye un plan de acción y hitos (POA&M).

Las limitaciones por control son:

- **GH-001:** no evalúa contenido ni calidad de la revisión, identidad del aprobador, análisis de impacto de seguridad/privacidad ni correspondencia entre revisión y código fusionado. El valor `2` es umbral interno.
- **GH-002:** no evalúa permisos efectivos, `CODEOWNERS`, verificaciones obligatorias, restricciones de push ni generación de registros de auditoría.
- **GH-003:** no valida la firma de cada commit, certificados, cadena de confianza, política de firma organizacional ni integridad de componentes instalados. `CM-05(03)` está retirado y trasladado a `CM-14`; SI-7 solo ofrece apoyo indirecto.

## Conservación del estado previo

El repositorio presentaba modificaciones y directorios no rastreados preexistentes antes de esta Fase 1. No se eliminaron ni modificaron esos elementos. El trabajo de esta fase se limita a los archivos documentales y de prueba descritos en el informe final.

## Estrategia de pruebas

- Se añaden pruebas unitarias que leen las reglas canónicas y comparan Rule ID, versión, estado activo, campos permitidos y condición canónica con la documentación.
- Se verifica que los tres controles canónicos estén documentados en la matriz y en las fichas, sin controles documentales huérfanos.
- Se verifica que cada ficha conserve la semántica triestado y la advertencia de correspondencia parcial; ninguna implica certificación.
- Se ejecutan las pruebas nuevas y la suite disponible; las pruebas que requieren PostgreSQL/Supabase pueden quedar omitidas si el entorno no dispone de esos servicios, y deben reportarse como tal.

## Criterios de aceptación

- Toda afirmación técnica sobre reglas se deriva del JSON canónico o del código; si no puede verificarse, se marca como pendiente de validación.
- Toda correspondencia NIST se declara explícitamente como parcial.
- No se altera el comportamiento observable del motor.
- Las pruebas de consistencia pasan con el directorio de reglas empaquetado por defecto.
- El informe final enumera archivos creados/modificados, resultados de pruebas, limitaciones y recomendaciones.
