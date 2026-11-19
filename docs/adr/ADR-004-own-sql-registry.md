# ADR-004 — Registro SQL propio vs pandera/Great Expectations

## Estado

Aceptado (18/11/2026).

## Contexto

Las 12 validaciones necesitan: niveles (fail/warn), gate que bloquee gold,
muestras de filas fallidas, conteos exactos y SQL citado en el reporte. El
mercado ofrece pandera (con backend PySpark) y Great Expectations.

## Decisión

Un **registro SQL propio** en `presupuesto/quality/registry.py`:

- Cada validación es una función pequeña que recibe el DataFrame de silver y
  devuelve `CheckResult` (name, layer, level, status, rows_checked,
  rows_failed, duration_ms, sql, failed_sample ≤ 20).
- El gate: cualquier check con `level=fail` y `status=fail` bloquea gold.
- Nada de checks escondidos dentro de los transforms; las validaciones leen
  silver con su propio SQL/DSL y no re-ejecutan transforms (nada tautológico).

## Consecuencias

### Positivas

- La validación 11 usa joins y agregación por ventana sin límite de la
  herramienta; artefactos 100% reproducibles.
- Cero dependencias extra; el reporte es JSON plano con checksum.
- Los E2E pueden exigir conteos exactos por validación (12/12 en el seed
  sucio).

### Negativas

- Menos "marca de herramienta" en el CV que pandera/GE.
- Sin ecosistema de validaciones pre-construidas: cada check se escribe a
  mano (12, acotado).

## Nota de implementación (Spark 4)

`Column.isin(contenedor)` evaluó silenciosamente a NULL en Spark 4.2 en esta
configuración; las validaciones usan comparaciones explícitas y
`left_anti` join. Registrado aquí para no repetir el pozo.
