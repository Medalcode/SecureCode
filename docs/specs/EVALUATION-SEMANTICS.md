# Contrato técnico de evaluación triestado

## Objetivo

Definir la semántica obligatoria de `PASS`, `FAIL` y `UNKNOWN` para todos los controles de SecureCode, independientemente del adaptador de evidencia o del repositorio de persistencia.

Esta especificación describe el comportamiento vigente del motor. No modifica reglas, umbrales ni código.

## Dominio

El resultado de una evaluación es exactamente uno de estos valores:

| Estado | Significado |
|---|---|
| `PASS` | Todas las condiciones requeridas se cumplen con evidencia completa. |
| `FAIL` | Existe al menos un incumplimiento comprobado. |
| `UNKNOWN` | No existe incumplimiento comprobado, pero falta evidencia necesaria para decidir. |

`UNKNOWN` no es un sinónimo de `FAIL` ni una categoría de riesgo. Representa una limitación de observabilidad: credenciales insuficientes, configuración ausente, error transitorio o campo no disponible.

## Condiciones atómicas

Para una condición sobre un campo de evidencia:

- Valor ausente o `None` → `UNKNOWN`.
- Comparación con operador no soportado → `UNKNOWN`.
- Tipo incompatible → `UNKNOWN`.
- Comparación evaluable y verdadera → `PASS`.
- Comparación evaluable y falsa → `FAIL`.

Los booleanos nunca se tratan como números. `True` no satisface `GTE 1` ni `EQ 1`.

## Conjunciones `AND`

La precedencia es:

1. Si alguna condición produce `FAIL`, el resultado es `FAIL`.
2. Si ninguna condición produce `FAIL` pero al menos una produce `UNKNOWN`, el resultado es `UNKNOWN`.
3. Si todas las condiciones producen `PASS`, el resultado es `PASS`.

En forma resumida: `FAIL > UNKNOWN > PASS` para una conjunción, donde `PASS` sólo se alcanza si todas las condiciones pasan.

Esta precedencia evita que una evidencia faltante no determinante oculte una violación ya demostrada.

## Disyunciones `OR`

Si una futura regla incorpora `OR`, deberá documentarse en su ficha antes de implementarse. Mientras tanto, las reglas canónicas vigentes utilizan `AND` o condiciones atómicas.

## Aplicación a GH-001

La regla canónica `GH-001-RULE v1` exige:

- `required_review_approvals >= 2` AND
- `dismiss_stale_reviews == true`.

Por la precedencia anterior:

| Aprobaciones | Descarte de obsoletas | Resultado |
|---|---|---|
| `>= 2` | `true` | `PASS` |
| `>= 2` | `false` | `FAIL` |
| `>= 2` | `null` | `UNKNOWN` |
| `< 2` | `true` | `FAIL` |
| `< 2` | `false` | `FAIL` |
| `< 2` | `null` | `FAIL` |
| `null` | `true` | `UNKNOWN` |
| `null` | `false` | `FAIL` |
| `null` | `null` | `UNKNOWN` |

## Contratos derivados

- El motor es puro y determinista: la misma evidencia produce siempre el mismo estado.
- El adaptador no decide el estado final; sólo normaliza evidencia.
- El repositorio no reinterpreta estados almacenados.
- Las explicaciones al usuario deben preservar el estado persistido, incluso si el análisis textual sugiere otra categoría.
- Un benchmark compatible con SecureCode debe adoptar esta precedencia para poder comparar etiquetas con el motor.

## Referencias

- `src/securecode/engine/executor.py`.
- `src/securecode/rules/GH-001.json`.
- `docs/specs/GH-001.md`.
- `docs/compliance/GH001_ORACLE_DISCREPANCY.md`.
