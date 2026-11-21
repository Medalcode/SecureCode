# Discrepancia formal del oráculo GH-001

## Estado

Documento informativo. No modifica reglas, umbrales, motor ni conjuntos de referencia.

## Fuentes revisadas

- Repositorio: `C:\Users\Jonatthan\Documents\Github\securecode-ground-truth`.
- Commit local observado: `f6a1db5ba90aaa3461f1663fed3240b2a0ffd252`.
- Manifiesto: `benchmark/manifest.json`, `benchmark_version=1.0.0`, `ground_truth_commit=f006fb843f13fa09fa4ae39d6c2b0570385b7c1e`.
- Conjunto sintético: `data/ground_truth/gh001_benchmark_105.json`, `dataset_version=1.0`, 105 casos.
- SHA-256 local verificado: `8319425d25a1b251f680282495e22a11043093397cf36afcd88a77a1529d7947`, coincide con `file_sha256` del manifiesto.
- Especificación: `docs/specs/GH001_ORACLE.md`, `Document Version=1.0`.

## Semánticas comparadas

- Oráculo v1.0: `UNKNOWN` prevalece si `required_review_approvals is None` o `dismiss_stale_reviews is None`; `FAIL` solo si ambas evidencias están completas y alguna incumple.
- Motor SecureCode actual: en una conjunción `AND`, `FAIL` prevalece si existe una violación conocida, aunque otra condición sea `UNKNOWN`; coincide con la ficha `docs/compliance/CONTROL-FICHES.md` y con la regla canónica `GH-001-RULE v1`.

## Resultado de la comparación

- Casos evaluados: 105.
- Coincidencias: 91.
- Discrepancias: 14.
- Todas las discrepancias son `expected=UNKNOWN`, `engine=FAIL`.

| Evidencia | Casos | Esperado por oráculo v1.0 | Motor SecureCode |
|---|---:|---|---|
| `A=None`, `D=False` | 9 | `UNKNOWN` | `FAIL` |
| `A=0`, `D=None` | 1 | `UNKNOWN` | `FAIL` |
| `A=1`, `D=None` | 4 | `UNKNOWN` | `FAIL` |

Casos exactos:

- `A=None, D=False`: `GT-GH001-BENCH-071`, `072`, `073`, `074`, `076`, `079`, `081`, `083`, `085`.
- `A=0, D=None`: `GT-GH001-BENCH-086`.
- `A=1, D=None`: `GT-GH001-BENCH-088`, `091`, `093`, `095`.

## Interpretación

La diferencia no está en el umbral ni en la condición canónica. Está en la precedencia triestado de la conjunción:

- Si la autoridad es el oráculo v1.0, el motor debería cambiar a precedencia `UNKNOWN`, lo cual alteraría la semántica actual y requiere aprobación formal, versión nueva de regla y revisión de resultados históricos.
- Si la autoridad es la semántica actual de SecureCode, el conjunto de referencia debe revisarse a versión `2.0`, dejando `expected_status=FAIL` para esos 14 casos y actualizando `GH001_ORACLE.md` con la precedencia `FAIL` sobre `UNKNOWN`.

## Propuesta formal

No aplicar cambios en esta fase. Solicitar decisión escrita del dueño del benchmark y del dueño de cumplimiento:

1. Confirmar cuál precedencia triestado es normativa.
2. Si se confirma `FAIL` prevalece: publicar oráculo v2.0 y dataset v2.0 con los 14 casos corregidos, recalcular hashes y actualizar `manifest.json`.
3. Si se confirma `UNKNOWN` prevalece: abrir cambio controlado de semántica del motor, con nueva versión de regla y plan explícito para no reescribir dictámenes históricos.

Hasta esa decisión, la discrepancia queda documentada como observación abierta, no como defecto corregido.

## Actualización Fase 7

Se formalizó la semántica vigente en `docs/specs/EVALUATION-SEMANTICS.md`: en una conjunción `AND`, `FAIL` prevalece sobre `UNKNOWN` cuando existe una violación comprobada.

Con esa semántica se preparó una propuesta v2 reproducible, sin modificar el dataset canónico externo:

- Dataset propuesto: `docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json`.
- Parche: `docs/benchmark/gh001/v2/gh001_benchmark_105_v2.patch.json`.
- Cambios y procedimiento: `docs/benchmark/gh001/v2/gh001_v2_change_report.md`.
- Métricas: `docs/benchmark/gh001/results/gh001_benchmark_comparison.md`.

v2 propuesto corrige 14 etiquetas de `UNKNOWN` a `FAIL`, mantiene los 105 identificadores y evidencias, y alcanza 105/105 coincidencias con el motor. No se declara adoptado oficialmente hasta la aprobación e incorporación del artefacto canónico en `securecode-ground-truth`.
