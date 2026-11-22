# Integridad documental contractual y aceptación

## Alcance

Verificación estática y dinámica del paquete documental usado en el registro público. No modifica textos legales ni declara revisión jurídica.

## Documentos públicos y documentos obligatorios

El sitio público publica seis documentos legales informativos en `src/securecode/api/public_site.py`:

| Ruta | Documento | Aceptación contractual |
|---|---|---|
| `/legal/terminos` | Términos de servicio | Sí, como `SERVICE_TERMS` |
| `/legal/privacidad` | Política de privacidad | No |
| `/legal/cookies` | Política de cookies | No |
| `/legal/eula` | Acuerdo de licencia de usuario final | No |
| `/legal/contratacion` | Condiciones de contratación y reembolsos | No |
| `/legal/sla` | Acuerdo de nivel de servicio | No |

El paquete obligatorio de registro no contiene seis documentos. Contiene exactamente dos, según `docs/specs/ORG-001.md:23-30`, `docs/specs/PUBLIC-001.md:29-30` y `src/securecode/api/service_documents.py:88-101`:

1. `SERVICE_TERMS` — `/legal/terminos`.
2. `TECHNICAL_SCOPE` — `/alcance`.

Los otros cuatro documentos legales son borradores académicos informativos, no requisitos de aceptación en este incremento. La mención a "6 documentos legales" en `docs/manuals/04-matriz-evidencia.md:76` describe el sitio público, no el paquete de aceptación.

## Paquete vigente y huellas observadas

Valores generados por `current_onboarding_package()` y publicados por `GET /api/v1/service-documents/current`:

- `package_id`: `SECURECODE-ONBOARDING`.
- `version`: `2026-11-20.1`.
- `package_sha256`: `0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b`.

| Documento | Versión | Ruta | SHA-256 del contenido |
|---|---|---|---|
| `SERVICE_TERMS` | `2026-11-20.1` | `/legal/terminos` | `d778d2f568e92ffd8c8272658270da5792330bc430c77cd4120b2a6f73f34632` |
| `TECHNICAL_SCOPE` | `2026-11-20.1` | `/alcance` | `ab9ff212c8576f8acc7416193dd0452193554726a18d8f30cc8129a1a96fe1fd` |

La huella del paquete se calcula sobre JSON canónico con `package_id`, `version`, `document_id`, `version`, `path` y `sha256` de cada documento. No es una concatenación ad hoc de los hashes individuales.

## Coherencia verificada

- `src/securecode/api/service_documents.py:17-18,29-31,49-65`: generación determinista de huellas.
- `src/securecode/api/app.py:246-258,447-450`: endpoint público que publica el mismo objeto que el generador.
- `tests/api/test_service_document_acceptance.py:56-71`: comprueba que el endpoint coincide con `current_onboarding_package().as_dict()`.
- `src/securecode/api/app.py:1092-1107`: cada fila de aceptación almacena `document_sha256`, `package_sha256`, versión, ruta y tipo de aceptación.
- `tests/api/test_service_document_acceptance.py:113-130`: comprueba que lo persistido coincide con el paquete publicado.
- `src/securecode/api/app.py:1115-1123`: evento de auditoría registra paquete, versión y hash sin secretos.
- `alembic/versions/f2b6c8d0a913_service_document_acceptances.py:19-39`: migración append-only para el historial de aceptaciones.
- `tests/integration/test_service_acceptance_migration.py`: validación de migración en base real.
- La fecha `15 de noviembre de 2026` de `src/securecode/api/public_site.py:16` es metadata del contenido público; la versión `2026-11-20.1` identifica el paquete contractual. No implican una contradicción de hash porque ambos valores participan de forma determinista en el contenido hulleado.

## Mecanismo implementado en Fase 7

Se incorporó una referencia independiente del contenido generado:

- Manifiesto: `docs/compliance/service_documents.manifest.json`.
- Carga verificada: `src/securecode/api/service_document_manifest.py`.
- Hash canónico esperado del manifiesto: `163bab7d53ec3efa7d6ad5f8838621d49e14f2499c7691e07b79c766288d67fc`, conservado como constante en código.
- `current_onboarding_package()` genera el paquete desde el contenido y falla si no coincide con el manifiesto verificado.
- `OrganizationRegistrationRequest` exige `accepted_document_package_sha256` y rechaza valores inexistentes o manipulados con `422`.
- La consola obtiene `package_id`, `version` y `sha256` desde `GET /api/v1/service-documents/current`; ya no fija esos valores en JavaScript.
- Cada aceptación conserva `document_sha256` y `package_sha256`; el evento de auditoría registra adicionalmente `accepted_document_manifest_version`.
- No se requirió migración: la tabla `service_document_acceptances` ya almacenaba las huellas y el historial es append-only.
- El aislamiento multiempresa no se modificó: el historial sigue siendo consultable sólo por el propietario de cada organización.

## Limitaciones del mecanismo

- El manifiesto y su constante de referencia residen en el mismo despliegue que el código y los documentos. Un atacante con capacidad de modificar todos esos artefactos podría alterar tanto el contenido como la referencia.
- Un hash SHA-256 demuestra integridad de bytes, no autenticidad de autoría ni aprobación jurídica.
- Para un nivel superior se requiere firma digital o manifiesto externo con cadena de custodia, llaves protegidas y verificación en arranque; eso queda fuera de esta fase por no introducir dependencias ni infraestructura nueva.
- La detección ocurre cuando se genera el paquete, se expone el endpoint o se intenta un registro; no sustituye controles de supervisión del entorno de despliegue.
