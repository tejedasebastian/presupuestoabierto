# Diccionario de datos — PresupuestoAbiertoPE v1.0.0

> Fuente: Consulta Amigable de Ejecución del Gasto (MEF/SIAF), año 2025.
> Cobertura: 1,892 municipalidades de 25 departamentos.
> Los archivos crudos no se commitean; esta documentación describe el contrato canónico.

## 1. Capas

| Capa | Formato | Contenido |
|---|---|---|
| `data/raw/*.xls` | HTML tabular | Exportaciones oficiales del MEF (28 archivos) |
| `data/medallion/bronze/budget_execution` | Delta | Filas canónicas crudas + `ingested_at`, `row_hash`, `concept_raw` |
| `data/medallion/silver/budget_execution` | Delta | Tipos, deduplicación y granos listos para calidad/gold |
| `data/medallion/silver/budget_execution_quarantine` | Delta | Filas estructuralmente inutilizables (por ahora: `accrued` nulo) |
| `data/medallion/gold/exec_by_entity` | Delta | Agregado anual por municipalidad + departamento + ranking |
| `data/medallion/gold/exec_monthly` | Delta | Serie mensual por entidad |
| `artifacts/e2e/*.csv|json` | Archivos | Payloads del run con checksums |

## 2. Granos (`grain`)

| Grano | Filas nacionales | Uso |
|---|---:|---|
| `department` | 25 | Agregado nacional por departamento |
| `entity_annual` | 1,892 | Ejecución anual por municipalidad |
| `entity_monthly` | 12 | Serie mensual (Miraflores) |
| `category_national` | 10 | Agregado nacional por genérica |

## 3. Campos canónicos (bronze/silver)

| Campo | Tipo | Descripción |
|---|---|---|
| `grain` | string | `department`, `entity_annual`, `entity_monthly`, `category_national` |
| `entity_ubigee` | string | Código UBIGEE de la entidad (6 dígitos) |
| `entity_code` | string | Código de pliego/municipalidad (hasta 6 dígitos) |
| `entity_name` | string | Nombre de la entidad tal como llega del MEF |
| `year` | int | Año de ejecución (2025) |
| `month` | int | Mes 1–12 (solo `entity_monthly`) |
| `category` | string | Genérica de gasto (solo `category_national`) |
| `category_code` | string | Código de genérica (`5-21`, `6-26`, …) |
| `department` | string | Departamento (contexto del manifiesto para archivos municipales) |
| `department_code` | string | Código INEI de departamento (`01`–`25`) |
| `pia` | decimal(18,2) | Presupuesto inicial |
| `pim` | decimal(18,2) | Presupuesto institucional modificado |
| `certification` | decimal(18,2) | Certificación |
| `annual_commitment` | decimal(18,2) | Compromiso anual |
| `monthly_commitment` | decimal(18,2) | Atención de compromiso mensual |
| `accrued` | decimal(18,2) | Devengado |
| `paid` | decimal(18,2) | Girado |
| `execution_pct` | double | Avance % de la fuente (no se usa para gold) |
| `query_date` | string | Fecha de la consulta del MEF |
| `source_file` | string | Archivo de origen |
| `ingested_at` | timestamp | Marca de ingesta |
| `row_hash` | string | SHA-256 de la fila canónica |
| `concept_raw` | string | Celda de concepto original (auditoría) |

## 4. Gold y exports

### `artifacts/e2e/execution_by_entity.csv`

| Columna | Tipo | Descripción |
|---|---|---|
| `entity_code` | string | Código de pliego |
| `entity_name` | string | Nombre de la entidad |
| `department` | string | Departamento (contexto) |
| `department_code` | string | Código de departamento |
| `pim_total` | double | PIM anual |
| `accrued_total` | double | Devengado anual |
| `execution_pct` | double | `accrued_total / pim_total * 100`; 0 si PIM = 0 |
| `rank` | int | Puesto nacional, 1 = mayor ejecución (empates por `entity_code`) |

### `artifacts/e2e/findings.json`

- `bottom_n`: las 10 municipalidades con menor ejecución, con departamento y PIM.
- `low_execution_alerts`: todas las municipalidades con `execution_pct < 60`.
- `categories`: agregado por genérica (10 filas de la fuente).
- `departments`: agregado por departamento (25 filas).
- `note`: “Findings describe budget execution, not intentions.”

### `artifacts/e2e/gold_summary.csv`

`metric,value`: `entities`, `avg_execution_pct`, `best_execution_pct`, `worst_execution_pct`, `low_execution_alerts`.

## 5. Modelo Power BI (TMDL)

| Tabla | Columnas principales | Medidas |
|---|---|---|
| `ExecutionByEntity` | `Municipalidad` (única), `Departamento`, `pim_total`, `accrued_total`, `execution_pct`, `rank` | `Municipalidades`, `Ejecución promedio`, `Alertas <60%`, `Puesto`, `PIM total`, `Devengado total`, `Ejecución % entidad` |
| `CategorySummary` | `label`, `Categoría`, `pim`, `accrued` | `Ejecución %`, `Brecha planillas-inversión` |
| `DepartmentSummary` | `label`, `Departamento`, `pim`, `accrued` | `Ejecución % departamento` |
| `QualitySummary` | `metric`, `Métrica`, `value` | `Valor` |

- `Municipalidad` es una columna calculada única: añade departamento cuando el nombre se repite y código de entidad si el homónimo persiste en el mismo departamento.
- Las tablas de contexto están desconectadas de `ExecutionByEntity`; son agregados nacionales y no deben cruzarse.
- El modelo usa `DataFolder` (parámetro TMDL) para localizar los CSV.

## 6. Reglas de calidad (12)

1. `raw_schema_present` — columnas PIA/PIM/DEVENGADO/GIRADO por archivo.
2. `raw_row_count` — el grano mensual debe tener ≥ 10 filas; el anual puede ser pequeño (Callao tiene 7 municipalidades).
3. `raw_parseable` — PIM parseable en filas anuales.
4. `silver_types` — tipos canónicos.
5. `silver_no_null_keys` — claves de entidad no nulas.
6. `silver_unique_keys` — unicidad por grano/entidad/mes/categoría.
7. `silver_catalog_referential` — catálogo mensual consistente.
8. `silver_entity_named` — entidades con nombre.
9. `business_devengado_le_pim` — devengado ≤ PIM.
10. `business_amounts_positive` — montos no negativos.
11. `business_monthly_sums_to_annual` — suma mensual = anual (tolerancia 1%).
12. `business_coverage_months` — cobertura mínima de meses.

El gate bloquea gold si cualquier check de nivel `fail` falla.
