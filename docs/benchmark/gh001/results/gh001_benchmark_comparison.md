# Resultados reproducibles del benchmark GH-001

## Estado

v1 se conserva como referencia histórica. v2 es una propuesta revisable, no adoptada oficialmente.

## Comandos

```bash
python scripts/build_gh001_v2_proposal.py --v1 <ruta-externa-a-gh001_benchmark_105.json>
python scripts/run_gh001_dataset_benchmark.py --dataset docs/benchmark/gh001/v1/gh001_benchmark_105_v1.snapshot.json --label gh001-v1-historical --output docs/benchmark/gh001/results/gh001_v1_metrics.json
python scripts/run_gh001_dataset_benchmark.py --dataset docs/benchmark/gh001/v2/gh001_benchmark_105_v2.proposed.json --label gh001-v2-proposed --output docs/benchmark/gh001/results/gh001_v2_proposed_metrics.json
```

## Resumen

| Métrica | v1 histórico | v2 propuesto |
|---|---:|---:|
| Casos | 105 | 105 |
| Coincidencias | 91 | 105 |
| Discrepancias | 14 | 0 |
| Exactitud global | 86.67% | 100.00% |
| Distribución esperada | PASS 35 / FAIL 35 / UNKNOWN 35 | PASS 35 / FAIL 49 / UNKNOWN 21 |
| Distribución observada | PASS 35 / FAIL 49 / UNKNOWN 21 | PASS 35 / FAIL 49 / UNKNOWN 21 |

## Métricas por clase — v1

| Clase | Soporte | Correctos | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| PASS | 35 | 35 | 1.000 | 1.000 | 1.000 |
| FAIL | 35 | 35 | 0.714 | 1.000 | 0.833 |
| UNKNOWN | 35 | 21 | 1.000 | 0.600 | 0.750 |

## Métricas por clase — v2 propuesto

| Clase | Soporte | Correctos | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| PASS | 35 | 35 | 1.000 | 1.000 | 1.000 |
| FAIL | 49 | 49 | 1.000 | 1.000 | 1.000 |
| UNKNOWN | 21 | 21 | 1.000 | 1.000 | 1.000 |

## Matriz de confusión — v1

| Esperado \ Observado | PASS | FAIL | UNKNOWN |
|---|---:|---:|---:|
| PASS | 35 | 0 | 0 |
| FAIL | 0 | 35 | 0 |
| UNKNOWN | 0 | 14 | 21 |

## Matriz de confusión — v2 propuesto

| Esperado \ Observado | PASS | FAIL | UNKNOWN |
|---|---:|---:|---:|
| PASS | 35 | 0 | 0 |
| FAIL | 0 | 49 | 0 |
| UNKNOWN | 0 | 0 | 21 |

## Interpretación

Las 14 discrepancias históricas se concentran en evidencia parcial con una violación comprobada. v2 ajusta únicamente esas etiquetas a `FAIL`, conforme al contrato de precedencia `FAIL > UNKNOWN` documentado en `docs/specs/EVALUATION-SEMANTICS.md`.

No se modificó el motor, la regla canónica ni la semántica de estados.
