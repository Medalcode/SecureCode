# GH-001 benchmark v2 propuesto

Artefacto propuesto, no adoptado oficialmente. El dataset canónico externo permanece intacto.

- Fecha: 2026-11-21
- Casos: 105
- SHA-256 de v1: `8319425d25a1b251f680282495e22a11043093397cf36afcd88a77a1529d7947`
- SHA-256 del archivo v2 propuesto: `1a8a3db4b597195096499c9d2f51e6d4df82260f400c8d9d9b585cdcccc5e278`
- SHA-256 canónico de casos v2: `0cff674610318d745a9dd136ac7c979c7aa465355944b9efa95a4c680ae7edf8`
- Distribución v1: PASS=35, FAIL=35, UNKNOWN=35
- Distribución v2: PASS=35, FAIL=49, UNKNOWN=21
- Coincidencias v1: 91/105
- Coincidencias v2: 105/105

## Cambios exactos

| ID | Evidencia | v1 | Motor | v2 propuesto | Justificación |
|---|---|---|---|---|---|
| GT-GH001-BENCH-071 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-072 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-073 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-074 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-076 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-079 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-081 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-083 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-085 | A=None, D=False | UNKNOWN | FAIL | FAIL | dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes |
| GT-GH001-BENCH-086 | A=0, D=None | UNKNOWN | FAIL | FAIL | required_review_approvals=0 es incumplimiento comprobado; FAIL prevalece sobre descarte ausente |
| GT-GH001-BENCH-088 | A=1, D=None | UNKNOWN | FAIL | FAIL | required_review_approvals=1 es incumplimiento comprobado; FAIL prevalece sobre descarte ausente |
| GT-GH001-BENCH-091 | A=1, D=None | UNKNOWN | FAIL | FAIL | required_review_approvals=1 es incumplimiento comprobado; FAIL prevalece sobre descarte ausente |
| GT-GH001-BENCH-093 | A=1, D=None | UNKNOWN | FAIL | FAIL | required_review_approvals=1 es incumplimiento comprobado; FAIL prevalece sobre descarte ausente |
| GT-GH001-BENCH-095 | A=1, D=None | UNKNOWN | FAIL | FAIL | required_review_approvals=1 es incumplimiento comprobado; FAIL prevalece sobre descarte ausente |

## Procedimiento de incorporación

1. Revisar y aprobar `docs/specs/EVALUATION-SEMANTICS.md` como contrato normativo.
2. Aplicar `gh001_benchmark_105_v2.patch.json` sobre una copia del dataset v1.
3. Verificar identificadores, evidencias y hash canónico contra `gh001_benchmark_105_v2.proposed.json`.
4. Publicar v2 en `securecode-ground-truth` con nueva versión de oráculo, manifiesto y hashes.
5. Actualizar la documentación de resultados de GH-001 sin reescribir los dictámenes históricos.

Este artefacto no declara adopción oficial de v2.
