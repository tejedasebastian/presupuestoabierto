# ROADMAP.md — PresupuestoAbiertoPE

> **Regla:** trabaja los checkpoints en orden. No saltes ninguno.
> **E2E-first:** el escenario se escribe antes de la implementación.
> **Un commit por checkpoint significativo.**
> **No avances si el E2E no pasa.**

---

## Fase 0 — Base del proyecto

- [x] Crear repo `presupuestoabierto` (privado primero).
- [x] Crear estructura `presupuesto/`, `data/raw/`, `data/medallion/`, `tests/e2e/`, `artifacts/e2e/`, `notebooks/`, `dashboard/`, `docs/`.
- [x] Configurar `pyproject.toml` con **Python 3.13**, `pyspark`, `delta-spark`, `pytest`, `ruff`.
- [x] Documentar requisitos locales: Java 17, `winutils.exe` + `hadoop.dll` para Windows, cerrar Docker (RAM).
- [x] Crear sesión Spark única en `shared/spark.py` (con Delta configurado).
- [x] Crear CLI mínimo `python -m presupuesto run --source smoke` que levanta Spark y escribe un Delta de prueba.
- [x] Crear CI con Java 17 + Python 3.13 que corre el E2E.
- [x] Crear `ADR-001: BYOD asistido + seed sintético` (`www.mef.gob.pe` tras Incapsula; Consulta Amigable viva en `apps5.mineco.gob.pe`; captura documentada en `data/raw/README.md`).
- [x] Crear `ADR-002: Spark local + Delta (Python 3.13 + Spark 4)`.
- [x] Crear `ADR-003: CI como orquestador`.
- [x] Crear `.env.example` y `.gitignore` (`data/raw/` y `data/medallion/` fuera de Git).

**E2E del checkpoint:**

- [x] El pipeline levanta Spark en local (y en CI tras el push).
- [x] Escribe un Delta de prueba en `data/medallion/smoke/`.
- [x] El CLI imprime un resumen JSON con `spark_version` y `delta_version`.

**Evidencia local:**

- `pytest tests/e2e -v` → **2 passed** (CLI smoke + sesión compartida).
- `python -m presupuesto run --source smoke` → JSON con `spark_version 4.2.0`, `delta_version 4.4.1`.
- `ruff format` y `ruff check` → All checks passed.

**Fixes de Windows descubiertos (documentados en ADR-002):**

- Hostname con guión bajo (`PC_ST25.mshome.net`) rompe el validador de URLs RPC de Spark → `SPARK_LOCAL_HOSTNAME=127.0.0.1`.
- `localhost` resuelve ambiguo (IPv6/IPv4) → `spark.driver.host/bindAddress=127.0.0.1`.
- Falta `hadoop.dll` → `UnsatisfiedLinkError` en NativeIO → instalada junto a `winutils.exe`.
- El JVM lanza workers con `python` a secas (stub de la Microsoft Store) → `PYSPARK_PYTHON=sys.executable`.
- La resolución Maven de Ivy se cuelga en esta red → jars de Delta vendored en `tools/jars/` montados vía `spark.jars` (`tools/fetch_jars.ps1` reproducible).

**Criterio de aceptación:**

- CI verde con Java 17 + Python 3.13.
- Spark y Delta importan sin errores en ubuntu (CI).
- No hay binarios pesados commiteados.

**Commit sugerido:**

```text
chore: initialize presupuestoabierto project
```

---

## Fase 1 — Seed sintético y bronze

- [x] Generador de seed determinista (`ingest/seed.py`):
  - modo `clean`: 25 departamentos + 50 municipalidades anuales + 2 municipalidades mensuales + 6 categorías reales,
  - modo `dirty`: una violación exacta por cada una de las 12 validaciones,
  - modo `volume`: 12,800 municipalidades equivalentes (perf, filas directas).
- [x] Lector BYOD (`ingest/byod.py`) de las tablas HTML-`.xls` de la Consulta Amigable (contrato verificado en `data/raw/README.md`): parse de filas, código `UBIGEE-PLIEGO`, montos con comas, encabezado con año y fecha de consulta.
- [x] Escritura bronze en Delta con `source_file`, `ingested_at`, `row_hash`.
- [x] Fallo explícito si faltan columnas obligatorias.
- [x] Determinismo: misma semilla → mismo bronze (mismos conteos).

**E2E del checkpoint:**

- [x] Seed clean → bronze con conteos exactos (filas, entidades, categorías, meses).
- [x] Seed dirty → bronze ingiere todo lo parseable (las violaciones se detectan después, en quality); archivos con fallo file-level se reportan explícitos.
- [x] HTML sintético estilo Consulta Amigable (fila `"150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES"`) → mapping correcto a bronze.
- [x] HTML sin columna `DEVENGADO` → error explícito con la lista de faltantes.
- [x] Re-ingesta del mismo archivo → no duplica filas (idempotente por overwrite).

**Evidencia local:**

- `pytest tests/e2e -v` → **8 passed** (Fase 0 + Fase 1).
- `python -m presupuesto run --source seed --mode clean` → JSON con `rows_ingested: 105`, `grain_counts` exactos, `files_parsed: 5`, `file_failures: []`.
- `ruff format` y `ruff check` → All checks passed.

**Criterio de aceptación:**

- [x] Bronze conserva el concepto original (`concept_raw`) + columnas canónicas + procedencia.
- [x] El E2E corre en CI sin red (el seed genera HTML local).
- [x] El seed es reproducible (montos deterministas por índice, sin RNG).

**Commit sugerido:**

```text
feat: add bronze ingestion and seed generator
```

---

## Fase 2 — Silver y cuarentena

- [x] Mapping español → inglés (columnas canónicas grain-aware, documentadas en `SPECS.md` 8.2).
- [x] Tipos: `year` int, `month` int (NULL en anual), montos decimal(18,2).
- [x] **Sin dedupe silencioso:** los duplicados los reporta la validación 6; silver no maquilla.
- [x] Cuarentena explícita (`silver.budget_execution_quarantine`) solo para filas estructuralmente inútiles (`accrued` nulo), con motivo por fila.
- [x] Escritura silver en Delta, idempotente.

**E2E del checkpoint:**

- [x] Seed clean → silver == bronze, 0 filas en cuarentena.
- [x] Seed dirty → la fila estructuralmente muerta va a cuarentena con motivo `null_accrued`; las violaciones de negocio **quedan en silver** para que quality las detecte.
- [x] Conservación exacta: `bronze == silver + cuarentena` (nada se pierde).
- [x] El E2E no re-ejecuta el transform para validar silver (nada tautológico): valida contra los datos.

**Evidencia local:**

- `pytest tests/e2e -v` → **12 passed** (Fases 0–2).
- Los E2E cazaron y fixearon dos bugs reales: el regex del año enganchaba el subtítulo y devolvía el año de la fecha de consulta; el seed dirty destruía la fila del mes 13 al reemplazar `rows[-1]`.
- `ruff format` y `ruff check` → All checks passed.

**Criterio de aceptación:**

- Ninguna fila se pierde sin registro: bronze = silver + cuarentena.
- El SQL de silver está en constantes nombradas, no inline en el CLI.
- Idempotencia verificada con doble corrida.

**Commit sugerido:**

```text
feat: add silver transforms with quarantine
```

---

## Fase 3 — Las 12 validaciones

- [x] Registro de validaciones (`quality/registry.py`): `name`, `layer`, `level`, `description`, `sql`.
- [x] Implementar las 12 validaciones de `SPECS.md` sobre silver (y 1–3 sobre bronze).
- [x] La validación 11 con join + agregación (`SUM OVER`/`GROUP BY`) sobre el acumulado mensual.
- [x] `quality_report.json`: status, conteos, `failed_sample` (≤ 20), `duration_ms` por validación.
- [x] Gate: cualquier `fail` detiene la construcción de gold; `warn` continúa.
- [x] Umbrales en `config.py`, no hardcodeados.
- [x] Crear `ADR-004: registro SQL propio vs pandera/Great Expectations`.

**E2E del checkpoint (el medio-difícil del proyecto):**

- [x] Seed **dirty** → el quality report detecta **12/12** validaciones con `rows_failed` exactos y muestras.
- [x] Seed clean → 12/12 `pass`, 0 warns, 0 cuarentena.
- [x] Con dirty, el gate **bloquea gold** y las validaciones con nivel `fail` quedan listadas en `blocking_checks`.
- [x] Los artefactos (`quality_report.json`) se escriben incluso cuando el gate falla (evidencia).

**Evidencia local:**

- `pytest tests/e2e/test_fase3_quality.py -v` → **3 passed** (clean 12/12 pass; dirty 12/12 detectadas con conteos exactos; campos de evidencia verificados).
- El gate del run sucio bloquea con 8 checks `fail` (archivo schema, archivo rowcount, mes 13, pliego nulo, duplicados, referencial 301999, devengado>PIM, PIM negativo).
- `ruff format` y `ruff check` → All checks passed.

**Bugs reales que los E2E cazaron en esta fase:**

- `isin(contenedor)` evalúa a NULL en Spark 4.2 → validaciones con joins explícitos (documentado en ADR-004).
- El regex de mes sin apóstrofe clasificaba departamentos de una palabra como meses (`01: AMAZONAS` → mes 01).
- V12 con 6 meses chocaba con `min_rows=10`: el archivo se saltaba y la violación jamás llegaba a silver.
- El duplicado V6 propagaba al join de la validación 11: el lado anual se deduplica (el duplicado ya lo reporta la 6).

**Criterio de aceptación:**

- [x] Ninguna validación tautológica ni change-detector.
- [x] Las 12 se listan en el report con su SQL.
- [x] Determinismo: mismas semillas → mismos `rows_failed`.

**Commit sugerido:**

```text
feat: add twelve quality validations
```

---

## Fase 4 — Gold y hallazgos

- [x] `gold.exec_monthly`: ejecución mensual por `(entity, month)`.
- [x] `gold.exec_by_entity`: totales y % ejecución anual con `ROW_NUMBER()` (empates resueltos por `entity_code`).
- [x] `gold.findings`: bottom-N municipalidades, categorías críticas, alertas < umbral y departamentos.
- [x] `findings.json` como artefacto con lenguaje neutral.
- [x] Export `execution_by_entity.csv` y `gold_summary.csv` para Power BI.

**E2E del checkpoint:**

- [x] Seed clean → gold con % de ejecución correcto (el E2E **recalcula** el esperado desde la fórmula del seed, no confía en el pipeline).
- [x] Rankings densos 1..50, orden descendente por % de ejecución.
- [x] Hallazgos: bottom-10, 8 alertas < 60% (exactas por construcción del seed), categorías y departamentos.
- [x] Dirty → gold **no existe** y el gold stale del run clean se elimina (no representa al dataset actual).

**Evidencia local:**

- `pytest tests/e2e/test_fase4_gold.py -v` → **3 passed**.
- Export CSV: 51 líneas (header + 50 entidades) con header estable verificado.
- `ruff format` y `ruff check` → All checks passed.

**Criterio de aceptación:**

- [x] Gold nunca se deriva de bronze (solo de silver validado).
- [x] Los porcentajes se recomputan desde montos (`accrued/pim`), nunca se confía en el `Avance %` del export; PIM = 0 → 0.0.
- [x] El E2E valida matemática de negocio, no solo “hay filas”.

**Commit sugerido:**

```text
feat: add gold aggregations and findings
```

---

## Fase 5 — Volumen, performance y BYOD real

- [x] Modo `volume` del seed (~934k filas a escala nacional en CI; 73k en la suite) para pruebas de performance.
- [x] Medir duración por etapa (bronze/silver/quality/gold) y registrarlo en `run_manifest.json`.
- [ ] Particionado de Delta por `year`/`month` donde aporte (medido, no adivinado) — **decisión documentada: no aporta a esta escala** (ver `docs/performance.md`; con 218 filas reales y ~934k sintéticas el particionado añade archivos pequeños sin ganancia medible).
- [x] **BYOD descargado (18/11/2026):** 4 archivos oficiales de la Consulta Amigable ya en `data/raw/` (departamentos nacional, municipalidades de Lima, Miraflores mensual, genéricas nacional); procedencia y hashes en `data/raw/README.md`.
- [x] **BYOD procesado:** run del pipeline sobre los archivos reales → **12/12 checks en verde**, 171 municipalidades en gold, 112.9 s totales.
- [x] Ajustar el adaptador al formato real (tablas HTML como `.xls`) y documentar el mapping aplicado.
- [x] Artículo de hallazgos con datos reales (`docs/findings-2025.md`).

**E2E del checkpoint:**

- [x] Volume: pipeline completo con conteos exactos y duraciones medidas por fase (E2E con 1,000 entidades; job de CI con 12,800 ≈ 934k filas).
- [x] BYOD real (local): run completo end-to-end con los 4 exports oficiales, quality report y hallazgos reales.
- [x] El manifest registra el SHA-256 de cada archivo BYOD como procedencia (verificado: coincide con `data/raw/README.md`).

**Evidencia local:**

- `pytest tests/e2e/test_fase5_volume.py -v` → **3 passed** (73,000 filas por el medallion completo; checksums recomputados y verificados).
- `python -m presupuesto run --source byod` → 218 filas, **12/12 checks pass**, gold con 171 entidades, 112.9 s.
- Hallazgos reales: peor municipalidad **Colonia 21.8%**; 9 alertas < 60%; promedio 84.7%; inversión (activos no financieros) 72.9% vs planillas 94.1%.
- `docs/findings-2025.md` y `docs/performance.md` con cifras medidas.

**Criterio de aceptación:**

- [x] Duraciones medidas, no estimadas.
- [x] Los hallazgos reales usan lenguaje neutral y citan la fuente y fecha.
- [x] Ningún CSV real se commitea (solo `byod_manifest.json` y el README de procedencia).

**Commit sugerido:**

```text
test: add volume scenario and byod adapter tuning
docs: add real data findings draft
```

---

## Fase 6 — Dashboard, docs y release

- [x] Dashboard autorado con la skill `powerbi-report-cli` (proyecto PBIP reproducible) y modelo con el MCP `powerbi-modeling`.
- [x] Capturas del tablero en Power BI Desktop (validadas; el guardado final del `.pbix` queda en manos del usuario).
- [x] Notebook wrapper de equivalencia Databricks (≤ 20 líneas, sin lógica).
- [x] README con capturas y métricas reales.
- [x] README.en.md.
- [x] Tag `v0.1.0` y release con artefactos.
- [x] Actualizar `Portafolio_Proyectos_Peru.md`.

**Evidencia del checkpoint:**

- PBIP `dashboard/PresupuestoAbiertoPE.pbip` con 2 páginas y 17 visuales; `validate` → **0 errores, 0 warnings**.
- Modelo TMDL: 4 tablas, 12 medidas; refresh completo verificado con 171 municipalidades, 84.7% promedio y 9 alertas.
- Capturas retenidas en `docs/screenshots/panorama.png` y `docs/screenshots/ranking.png` (Desktop, escala 2).
- Notebook `notebooks/databricks_equivalence.py` (9 líneas efectivas, sin lógica de negocio).
- README y README.en.md con demo, métricas reales y enlace a `docs/dashboard.md`.
- `Portafolio_Proyectos_Peru.md` actualizado con estado v0.1.0, stack y métricas reales.
- Release `v0.1.0` con 8 artefactos BYOD (6 payloads + manifest + checksums) y `CHANGELOG.md`.

**E2E del checkpoint:**

- Todos los artefactos existen con checksums verificados.
- El pipeline corre desde cero en CI (clon limpio) en una sola acción.
- Los exports CSV abren en Power BI sin reparaciones.

**Criterio de aceptación:**

- Todos los checkpoints técnicos anteriores marcados.
- E2E verde y reproducible (clean + dirty + contract + idempotencia).
- README y README.en.md completos.
- No hay PII, secretos ni archivos BYOD commiteados.
- Tag y release creados.
- El BYOD real quedó documentado como evidencia (el paso manual del `.pbix` y del post de LinkedIn queda en manos del usuario).

**Commits sugeridos:**

```text
feat: add dashboard evidence pack
docs: finalize v0.1.0
chore: release v0.1.0
```

---

## Fase 7 — v1.0.0 nacional 2025

- [x] Descargar las 25 exportaciones BYOD departamentales (más agregados nacionales y serie mensual) y registrar el manifiesto de 28 archivos.
- [x] Ajustar el parser y el manifiesto: contexto `department`/`department_code` y `min_rows` solo para el grano mensual.
- [x] Añadir `department` a gold, CSV y modelo TMDL; `Municipalidad` única para homónimos.
- [x] Dashboard nacional: bottom-10 nacional, 6 genéricas, bottom-7 de 25 departamentos, ranking de 1,892 con filtro por departamento + búsqueda.
- [x] Capturas nacionales en `docs/screenshots/`.
- [x] PBIX nacional en Git (240,165 bytes, 1,892 filas, generado desde el PBIP).
- [x] Diccionario de datos y diagrama de arquitectura.
- [ ] Test con una persona externa (kit en `docs/user-test-v1.0.0.md`; pendiente de ejecutar).
- [x] Tag y release `v1.0.0`.

**Evidencia del checkpoint:**

- 28 archivos, **1,939 filas**, **1,892 municipalidades**, **25 departamentos**, 0 filas en cuarentena.
- **12/12 validaciones**; gate abierto; gold con 1,892 entidades y 12 filas mensuales.
- Ejecución promedio **79.5%**; **196 alertas <60%**; peor **Eleazar Guzmán Barrón (Áncash) 13.2%**; brecha planillas-inversión **21.2 pp**.
- Run nacional **129.4 s** (bronze 34.7 s, silver 30.3 s, calidad 20.9 s, gold 25.6 s).
- PBIR `validate` → **0 errores, 0 warnings**; modelo TMDL 4 tablas / 11 medidas; Desktop refrescado con 1,892 filas.
- Capturas en `docs/screenshots/panorama.png` y `ranking.png`.
- Manifiesto con SHA-256 de los 28 archivos fuente y checksums de los 6 payloads.
- PBIX nacional `dashboard/PresupuestoAbiertoPE.pbix` (240,165 bytes).
- Release `v1.0.0` con 8 artefactos: https://github.com/kuki236/presupuestoabierto/releases/tag/v1.0.0
- CI verde en el commit de release: pipeline 17m22s + volume 41s.

**Criterio de aceptación:**

- [x] Cobertura nacional y 12/12 con datos reales.
- [x] Dashboard nacional validado y capturado.
- [x] Documentación de datos, arquitectura y hallazgos.
- [x] Release `v1.0.0` con 8 artefactos y CI verde.
- [x] PBIX nacional en Git (`dashboard/PresupuestoAbiertoPE.pbix`, 240,165 bytes).
- [ ] Feedback de una persona externa.

---

## Definición de terminado

Un checkpoint está terminado cuando:

- [x] El E2E del checkpoint pasa.
- [x] El artefacto correspondiente existe y es reproducible.
- [x] El checkbox está marcado.
- [x] `README.md` está actualizado si cambió algo visible.
- [x] `ruff format` y `ruff check` pasan.
- [x] No hay PII, secretos ni datos crudos commiteados.
- [x] El commit está hecho.

El proyecto está terminado cuando:

- [ ] Todos los checkpoints técnicos están marcados.
- [ ] El E2E medio-difícil pasa desde cero (dirty 12/12 + clean → hallazgos).
- [ ] El pipeline corre en CI sin tocar la red real.
- [ ] El BYOD real del MEF se procesó al menos una vez en local.
- [ ] Los hallazgos con datos reales existen y son regenerables.
- [ ] README y README.en.md están completos.
- [ ] La licencia y los créditos están claros.
- [ ] El tag `v0.1.0` y el release con artefactos están creados.

---

## Reglas de avance

- No avances si el E2E falla.
- No modifiques fixtures para hacer pasar un test.
- No agregues features fuera del alcance del MVP.
- Si el archivo BYOD real no calza en el contrato, detente y propón opciones.
- Si una validación da falsos positivos con datos reales, ajusta el umbral con evidencia, no para “hacer pasar”.
- Si rompes un boundary, justifícalo en un ADR.

---

## Backlog v0.2 (no ahora)

- MinIO free tier como storage del medallion.
- Prefect para orquestación programada.
- Databricks como entorno alternativo verificado.
- Multi-año y datos de ingresos.
- Publicación del dashboard en Power BI Service.
- Comparación con SEACE (contrataciones de las mismas municipalidades).
- pandera como segunda capa de validación (evaluación).
