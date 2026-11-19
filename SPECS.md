# SPECS.md — PresupuestoAbiertoPE

> **Producto:** PresupuestoAbiertoPE — Pipeline de datos abiertos con calidad y nube.
> **Versión:** 0.1 (MVP).
> **Fecha:** 18 de noviembre de 2026.
> **Estado:** especificación cerrada; implementación pendiente.
> **Documentación:** español. **Código y commits:** inglés.

---

## 1. Resumen

PresupuestoAbiertoPE es un **pipeline de datos local-first** que convierte la ejecución presupuestal de municipalidades (exportaciones oficiales del MEF) en un medallion **bronze → silver → gold** con **12 validaciones de calidad**, y produce hallazgos comparables: qué municipalidades ejecutan menos, en qué categorías y en qué meses.

El flujo es:

1. El usuario descarga una exportación oficial (HTML-`.xls`) de la **Consulta Amigable del MEF** (BYOD: bring your own data).
2. El pipeline lo ingiere a **bronze** (crudo + procedencia).
3. Lo transforma a **silver** (tipos, dedupe, catálogos, cuarentena).
4. Ejecuta las **12 validaciones de calidad** y produce un quality report.
5. Si el gate pasa, construye **gold**: % de ejecución por municipalidad, categoría y mes.
6. Genera **hallazgos** (menor ejecución, categorías críticas) y exports para Power BI.

En CI, todo corre sobre un **seed sintético determinista** (limpio y sucio); nunca se llama al MEF.

---

## 2. Problema

Los datos de ejecución presupuestal de las municipalidades están dispersos y son difíciles de comparar. La Consulta Amigable del MEF permite consultar pliego por pliego, pero no comparar todos a la vez. Ciudadanos, periodistas y gobiernos locales no tienen un tablero simple para detectar baja ejecución o prioridades.

Este proyecto demuestra, además, el oficio completo de data engineering: ingesta, arquitectura medallion, calidad de datos con gate, agregaciones con SQL real y hallazgos honestos.

---

## 3. Usuarios

### Usuario principal

- El autor del proyecto, como data engineer en formación: corre el pipeline, lo valida y escribe los hallazgos.
- Periodistas de datos que quieran replicar el análisis con su propio CSV.

### Usuario secundario

- Ciudadanos y funcionarios de gobiernos locales que quieran un punto de partida para comparar ejecución.

### Fuera de alcance

- Consumo automatizado desde el MEF (el sitio bloquea bots; ver sección 5).
- Datos de personas naturales (no existen en la fuente).
- Recomendaciones de política pública; solo descripción de ejecución.

---

## 4. Principios de producto

1. **BYOD (bring your own data):** el usuario trae la exportación oficial del MEF (HTML-`.xls`); el pipeline no navega.
2. **Local-first y reproducible:** el medallion vive en tu máquina; CI lo reproduce con seed sintético.
3. **Calidad con gate:** sin silver validado no hay gold; las validaciones son ciudadanas del pipeline, no un adorno.
4. **Honesto:** los hallazgos describen ejecución, no intenciones; ninguna métrica inventada.
5. **Idempotente:** re-ejecutar el pipeline no duplica datos ni hallazgos.
6. **Equivalencias documentadas:** Spark local + Delta es el motor; Databricks queda como documentación de equivalencia, no como dependencia.

---

## 5. Realidad de las fuentes (evidencia verificada)

| Fuente | Estado verificado (17–18/11/2026) |
|---|---|
| `www.mef.gob.pe` (transparencia, consulta amigable) | ❌ Tras **Incapsula** (WAF anti-bot): devuelve shell de 212 bytes en todas las rutas |
| `apps.mef.gob.pe/consultaamigable/` | ❌ Mismo WAF; la app antigua está muerta ("La página solicitada no está disponible") |
| `consultamensual.mef.gob.pe` | ❌ Dominio caído |
| CKAN nacional `datosabiertos.gob.pe` | ✅ Funciona, pero el MEF no publica ahí el consolidado municipal (solo 3 datasets, ninguno útil) |
| "Detalle por genérica 2016" en el CKAN | ❌ Es un espejo del portal de **Miraflores**, no consolidado |
| **`apps5.mineco.gob.pe/transparencia/Navegador/Navegar_7.aspx`** | ✅ **La Consulta Amigable real, viva y sin WAF.** Hallada vía Bing (18/11/2026) |

**Conclusión (actualizada):** la Consulta Amigable vive en `apps5.mineco.gob.pe` (dominio antiguo del MEF), sin Incapsula. La navegación por drill-down (Nivel de Gobierno → Gobiernos Locales → Municipalidades → Departamento → Municipalidad) y su botón "Exportar" generan **URLs GET sin estado** que devuelven la tabla. La descarga por el navegador falla en esta máquina (la app corre en un iframe y Chrome bloquea la descarga con archivos `.tmp` efímeros), así que la captura asistida usa el **GET directo de la URL de exportación que el propio navegador generó** — una petición puntual por archivo, iniciada por el usuario, sin crawling. El pipeline se diseña BYOD + seed sintético para CI.

### Set BYOD capturado (18/11/2026)

Cuatro archivos oficiales, año 2025, ya en `data/raw/` (gitignored):

| Archivo | Contenido | Filas aprox. |
|---|---|---|
| `consulta_amigable_departamentos_2025.xls` | Municipalidades de todo el Perú agregadas por departamento | 25 |
| `consulta_amigable_lima_municipalidades_2025.xls` | Todas las municipalidades del departamento de Lima, con código `UBIGEE-PLIEGO` | ~170 |
| `consulta_amigable_miraflores_mes_2025.xls` | Serie mensual (12 meses) de Miraflores | 13 |
| `consulta_amigable_municipalidades_generica_2025.xls` | Municipalidades del Perú agregadas por genérica de gasto | 7 |

Procedencia completa (URLs de exportación y SHA-256) en `data/raw/README.md`.

### Contrato de entrada BYOD (verificado con archivos reales)

Los "CSV" de la Consulta Amigable son en realidad **tablas HTML exportadas con extensión `.xls`** (exportación ASP.NET clásica). El adaptador bronze parsea HTML, no CSV plano.

Estructura de una fila de datos:

```text
Concepto                          → entity_code + entity_name
PIA                               → pia_amount
PIM                               → pim_amount
Certificación                     → certification_amount
Compromiso Anual                  → annual_commitment_amount
Atención de Compromiso Mensual    → monthly_commitment_amount
Devengado                         → accrued_amount
Girado                            → paid_amount
Avance %                          → execution_pct
```

Formatos reales descubiertos:

- **Entidades**: `"150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES"` — código compuesto `UBIGEE-PLIEGO` + nombre. El adaptador lo separa en `entity_code` (pliego, p. ej. `301271`) y `entity_name`.
- **Meses**: `"1: 'Enero"` … `"12: 'Diciembre"`.
- **Categorías**: `"5-21: PERSONAL Y OBLIGACIONES SOCIALES"` — código genérica.
- **Montos**: strings con comas de miles (`"387,456,981"`); vacíos en algunas vistas mensuales.
- **Encabezado del archivo** incluye `Fecha de la Consulta` y `Año de Ejecución` — el adaptador los lee como metadatos de procedencia.

**Nota crítica (corregida con evidencia):** la vista "Mes" de la Consulta Amigable exporta **devengado del mes**, NO acumulado. La validación 11 usa ese contrato: consistencia entre la suma mensual y el total anual. Si aparece un formato acumulado, el adaptador lo declara en el manifest y la validación se ajusta de forma documentada — nunca en silencio.

Si falta una columna obligatoria, el pipeline **falla en bronze** con un error explícito que lista las columnas faltantes y sugiere qué reporte descargar.

---

## 6. Alcance del MVP (v0.1)

### Incluido

- Ingesta BYOD de un CSV del MEF (un año, pliegos municipales).
- Seed sintético determinista: modo limpio y modo sucio (12 violaciones).
- Medallion bronze → silver → gold en **Delta Lake** sobre filesystem.
- 12 validaciones de calidad con niveles `fail`/`warn`, cuarentena y gate.
- Gold: % de ejecución por municipalidad, categoría y mes; rankings con window functions.
- Hallazgos: bottom-N de ejecución, categorías críticas, alertas de baja ejecución.
- Exports CSV de gold para Power BI + evidencia del dashboard.
- Artículo de hallazgos (borrador con datos reales cuando el BYOD esté).
- CI (GitHub Actions) corriendo el pipeline completo sobre seed.
- E2E medio-difícil con artefactos y checksums.
- Notebook wrapper de equivalencia con Databricks (≤ 20 líneas, sin lógica).

### Fuera del MVP

- Scrapeo del MEF o de cualquier WAF.
- Multi-año (el diseño lo permite; v0.1 procesa un año).
- MinIO/S3 real (documentado como equivalencia; Docker es inestable en la máquina actual).
- Prefect server (CI es el orquestador; Prefect queda como v0.2).
- Databricks como motor requerido.
- Dashboard publicado en Power BI Service.
- Datos de ingresos (solo gastos) y comparación con SEACE.

---

## 7. Arquitectura

### 7.1 Medallion

```text
                    BYOD (navegador humano)
                            │
                            ▼
                   data/raw/*.csv  (gitignored)
                            │
                ┌───────────▼────────────┐
                │ ingest: byod / seed     │
                └───────────┬────────────┘
                            ▼
   ┌─────────────────────────────────────────────┐
   │ BRONZE (Delta)  data/medallion/bronze/       │
   │ fila cruda + source_file + ingested_at       │
   └───────────────────────┬─────────────────────┘
                           ▼
   ┌─────────────────────────────────────────────┐
   │ SILVER (Delta)  data/medallion/silver/       │
   │ tipos, dedupe, catálogos, cuarentena         │
   └───────────────┬─────────────────────────────┘
                   ▼
   ┌─────────────────────────────────────────────┐
   │ QUALITY: 12 validaciones sobre silver        │
   │ quality_report.json (gate: fail detiene gold)│
   └───────────────┬─────────────────────────────┘
                   ▼ (solo si el gate pasa)
   ┌─────────────────────────────────────────────┐
   │ GOLD (Delta)  data/medallion/gold/           │
   │ exec_monthly, exec_by_entity, findings       │
   └───────────────┬─────────────────────────────┘
                   ▼
        artifacts/e2e/ + exports CSV + dashboard/
```

### 7.2 Contextos

| Contexto | Responsabilidad | No debe hacer |
|---|---|---|
| `ingest` | BYOD (HTML-`.xls`) y seed → bronze | Validar negocio |
| `transform` | bronze → silver | Ejecutar validaciones |
| `quality` | 12 validaciones sobre silver | Transformar datos |
| `analytics` | silver → gold, hallazgos | Leer bronze |
| `reporting` | Artefactos, exports, evidencia dashboard | Calcular métricas de negocio |
| `shared` | Spark, config, logging, errores | Lógica de negocio |

### 7.3 Reglas de boundaries

- La sesión Spark se crea una sola vez (`shared.spark`).
- El SQL de negocio vive en `transforms` y `analytics`, como constantes nombradas.
- Las validaciones leen **silver** con SQL propio; nunca re-ejecutan un transform.
- Gold solo se construye si el gate de calidad pasa.
- El CLI (`__main__.py`) orquesta llamando a los contextos; no calcula nada.
- Notebooks: wrappers delgados para equivalencia con Databricks.

---

## 8. Modelo de datos

### 8.1 Bronze — `bronze.budget_execution_raw`

Fila cruda del CSV + metadatos de procedencia. Columnas fuente en español tal cual, más:

- `source_file: string` (nombre del archivo BYOD o `seed`)
- `ingested_at: timestamp`
- `row_hash: string` (SHA-256 de la fila canónica, para dedupe)

### 8.2 Silver — `silver.budget_execution`

| Columna | Tipo | Origen (español → inglés) |
|---|---|---|
| `entity_code` | string | pliego extraído de `"UBIGEE-PLIEGO: NOMBRE"` (p. ej. `301271`) |
| `entity_name` | string | nombre de la entidad |
| `entity_ubigee` | string | ubigeo extraído del código compuesto (p. ej. `150122`) |
| `government_level` | string | derivado del rango del pliego (GL) |
| `year` | int | AÑO EJECUCIÓN |
| `month` | int (1–12) | MES / Periodo |
| `category` | string | GENÉRICA / Categoría |
| `category_code` | string | mapeado desde catálogo |
| `pia_amount` | decimal(18,2) | PIA |
| `pim_amount` | decimal(18,2) | PIM |
| `accrued_amount` | decimal(18,2) | DEVENGADO (del mes en vistas mensuales; anual en vistas anuales) |
| `source_file` | string | procedencia heredada |

Clave de negocio: `(year, month, entity_code, category_code)`, única.

Filas inválidas van a `silver.budget_execution_quarantine` con el motivo; **no se pierden**, se reportan.

### 8.3 Gold

- `gold.exec_monthly` — `(year, month, entity_code, entity_name, category, pim, accrued, execution_pct)`
- `gold.exec_by_entity` — `(year, entity_code, entity_name, pim_total, accrued_total, execution_pct, rank)` con `RANK()`/`ROW_NUMBER()`
- `gold.findings` — hallazgos materializados:
  - bottom-N municipalidades por % ejecución,
  - categorías con menor ejecución promedio,
  - alertas de baja ejecución (threshold configurable, p. ej. < 60%).

### 8.4 Artefactos del run

```text
artifacts/e2e/
├─ run_manifest.json        # modo, fuente, conteos, duración, checksums
├─ quality_report.json      # 12 validaciones con conteos y muestras
├─ findings.json            # hallazgos materializados
├─ execution_by_entity.csv  # export para Power BI
├─ gold_summary.csv         # resumen legible
└─ checksums.sha256         # hashes de los artefactos de payload
```

---

## 9. Las 12 validaciones

Niveles: `fail` detiene la construcción de gold; `warn` se reporta y continúa.

| # | Nombre | Capa | Nivel | Qué verifica | Modo de fallo detectable |
|---|---|---|---|---|---|
| 1 | `raw_schema_present` | bronze | fail | Columnas obligatorias presentes en el CSV | Falta `DEVENGADO`, `PLIEGO`, etc. |
| 2 | `raw_row_count` | bronze | fail | Filas ≥ `min_rows` (config) | Archivo vacío o truncado |
| 3 | `raw_parseable` | bronze | warn | % de filas numéricas parseables ≥ umbral | `"1.2xx3"` en PIM |
| 4 | `silver_types` | silver | fail | `year` int, `month` 1–12, montos decimal ≥ 0 | Mes 13, año `"20X6"` |
| 5 | `silver_no_null_keys` | silver | fail | Clave `(year, month, entity_code, category_code)` sin nulos | Mes vacío |
| 6 | `silver_unique_keys` | silver | fail | Sin filas duplicadas en la clave | Fila repetida |
| 7 | `silver_catalog_referential` | silver | fail | `entity_code` ∈ catálogo de pliegos | Pliego 9999 inexistente |
| 8 | `silver_entity_named` | silver | warn | `entity_name` no vacío ni placeholder | `"SIN DATO"`, `"-"` |
| 9 | `business_devengado_le_pim` | silver | fail | `accrued_amount ≤ pim_amount` por fila | Devengado 150% del PIM |
| 10 | `business_amounts_positive` | silver | fail | PIA, PIM y devengado ≥ 0 | PIM negativo |
| 11 | `business_monthly_sums_to_annual` | silver | warn | Suma de devengado mensual ≈ total anual por `(entity, category, year)`, con `SUM OVER`/`GROUP BY` | Diciembre devengado = 0 con 11 meses activos |
| 12 | `business_coverage_months` | silver | warn | Cobertura de meses por `(entity, category)` ≥ umbral | Entidad con solo 6 meses |

Cada validación produce en el report: `name`, `layer`, `level`, `status`, `rows_checked`, `rows_failed`, `failed_sample` (≤ 20), `duration_ms`, `sql`.

**Elección documentada (ADR-004):** las validaciones son un **registro SQL propio** en Spark, no pandera/Great Expectations. Tradeoff: menos “marca de herramienta”, pero cero dependencia que limite SQL avanzado (la 11 usa agregación por ventana) y artefactos 100% reproducibles. pandera queda como backlog de evaluación.

---

## 10. Flujo de ejecución

```powershell
# local, con datos BYOD reales
python -m presupuesto run --source byod --file data/raw/consulta_amigable_lima_municipalidades_2025.xls

# local, con seed limpio (demo reproducible)
python -m presupuesto run --source seed --mode clean

# local, con seed sucio (las 12 violaciones, para demo del gate)
python -m presupuesto run --source seed --mode dirty

# CI (GitHub Actions) corre: seed clean + seed dirty + asserts de artefactos
```

El CLI ejecuta los contextos en orden, escribe artefactos y termina con un resumen: filas procesadas, cuarentena, resultado de validaciones, hallazgos y duración.

---

## 11. Orquestación

- **CI como orquestador** (decisión del usuario): GitHub Actions ejecuta el pipeline completo (seed clean + dirty) en cada push, con Java 17 + Python 3.13 + caché de pip. CI es la validación autoritativa.
- Local: un comando (`python -m presupuesto run ...`) dispara todo.
- **Prefect** y **MinIO** quedan como backlog v0.2 documentado como equivalencias (el portafolio original los menciona; no agregan valor al MVP y Docker es inestable en la máquina actual).

---

## 12. Dashboard (Power BI)

- Los exports de gold (`execution_by_entity.csv`, `gold_summary.csv`) son la fuente del tablero.
- El reporte se autorra de forma reproducible con la skill `powerbi-report-cli` (proyecto PBIP); el modelo semántico con el MCP `powerbi-modeling`.
- Power BI Desktop está instalado (confirmado por el usuario): sirve para verificar, visualizar y generar capturas.
- El paso manual se reduce a abrir/verificar el PBIP y publicar capturas; la autoría del reporte no depende de pasos manuales.
- Criterios del tablero:
  - % de ejecución por municipalidad (mapa/barra),
  - serie mensual por categoría,
  - top/bottom N,
  - alertas de baja ejecución.

---

## 13. Métricas

Solo se reportan métricas medidas por el propio pipeline:

| Métrica | Fuente |
|---|---|
| Registros procesados (bronze/silver/gold) | `run_manifest.json` |
| Municipalidades cubiertas | `gold.exec_by_entity` |
| Score de calidad (12/12, warns) | `quality_report.json` |
| Duración por etapa | `run_manifest.json` |
| Filas en cuarentena y su motivo | `silver.*_quarantine` |
| Hallazgos (bottom-N, categorías críticas) | `findings.json` |

No se inventan métricas. El artículo de hallazgos solo usa números regenerables con un comando.

---

## 14. Testing

### Estrategia

- **E2E-first.** Escenario antes que implementación.
- **Sin unit tests después del código.**
- Escenario **medio-difícil**: el seed sucio inyecta exactamente una violación por validación; el E2E exige 12/12 detectadas con conteos exactos y el gate bloqueando gold.
- Artefactos repetibles con checksums.
- CI jamás llama al MEF.

### Escenarios E2E principales

1. **Clean:** seed limpio → bronze → silver (0 cuarentena) → 12/12 pass → gold → hallazgos → artefactos.
2. **Dirty:** seed sucio → 12/12 detectadas con conteos exactos → `fail` detiene gold → artefactos igualmente escritos (evidencia del gate).
3. **BYOD contract:** CSV sintético con encabezados estilo Consulta Amigable → mapping correcto a silver.
4. **Idempotencia:** correr dos veces no duplica filas ni hallazgos.
5. **Rerun determinista:** mismo seed → mismos conteos y hallazgos.

---

## 15. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El archivo BYOD real no coincide con el contrato | El adaptador falla explícito listando columnas faltantes; el usuario elige otro reporte |
| Devengado mensual vs acumular según reporte | El manifest declara el modo; la validación 11 se ajusta documentada |
| Windows + Spark (winutils) | Instalación documentada una vez; CI ubuntu es la validación autoritativa |
| RAM local ajustada (~2 GB libres requeridos) | Documentar: cerrar Docker antes de correr local |
| delta-spark 4.x en Windows local menos documentado que en Linux | `winutils.exe` documentado una vez; CI (ubuntu) valida autoritativamente |
| Falsos positivos en valid 9/11 con datos reales | Umbrales configurables + nivel `warn` donde el MEF tiene idiosincrasias |
| Docker inestable en la máquina | Nada del MVP depende de contenedores |

---

## 16. Decisiones

### Tomadas

- Fuente: **BYOD del MEF + seed sintético** (Incapsula bloquea `www.mef.gob.pe`, verificado). La Consulta Amigable real vive en `apps5.mineco.gob.pe` sin WAF; captura asistida vía navegador del usuario (browser MCP) y, cuando Chrome bloquea la descarga del iframe, **GET puntual de la URL de exportación generada por el propio navegador** — una petición por archivo, sin crawling.
- Motor: **Spark local + Delta Lake** (pip), Java 17 presente; Databricks como documentación de equivalencia.
- Dashboard: Power BI Desktop confirmado; autoría reproducible con `powerbi-report-cli` (PBIP) + `powerbi-modeling`.
- Python **3.13** + PySpark 4.2 + delta-spark 4.4: verificado con `pip --dry-run` (resuelven `pyspark-4.2.0` y `delta_spark-4.4.1`); Spark 4 requiere Java 17, ya instalado.
- Orquestación: **CI como orquestador**; Prefect/MinIO en backlog v0.2.
- Validaciones: registro SQL propio (12), no pandera/GE.
- Docs en español; código, columnas silver/gold y commits en inglés.
- **BYOD ya capturado (18/11/2026):** 4 archivos oficiales 2025 (departamentos nacional, municipalidades de Lima, Miraflores mensual, genéricas nacional) en `data/raw/`, con hashes en `data/raw/README.md`.

### Pendientes

- ~~Año y alcance exacto del CSV BYOD~~ → **Resuelto (18/11/2026):** año 2025; departamento Lima a nivel municipal + contexto nacional.
- El pipeline aún no procesa los BYOD: ocurre en Fase 1 (adaptador) y Fase 5 (run completo con datos reales).
- Si el dashboard se arma con la herramienta de PBIP o manualmente (se decide en Fase 6).

---

## 17. No objetivos

- No scrapear el MEF ni ningún WAF.
- No ser un sistema de denuncias: describe ejecución, no intenciones.
- No procesar multi-año ni ingresos en v0.1.
- No depender de Databricks, MinIO ni Prefect para el MVP.
- No publicar el dashboard en Power BI Service en v0.1.
- No reemplazar la fuente oficial del MEF; PresupuestoAbiertoPE no está afiliado.
