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

- [ ] Mapping español → inglés (constante única, documentada en `SPECS.md`).
- [ ] Tipos: `year` int, `month` 1–12, montos decimal(18,2).
- [ ] Dedupe por `(year, month, entity_code, category_code)`.
- [ ] Resolución de catálogos: pliegos y categorías (`data/catalogs.py`).
- [ ] Cuarentena explícita (`silver.budget_execution_quarantine`) con motivo por fila.
- [ ] Escritura silver en Delta, idempotente.

**E2E del checkpoint:**

- Seed clean → silver 0 filas en cuarentena, 0 duplicados, clave única.
- Seed dirty → las filas malas van a cuarentena con el motivo correcto; las filas buenas siguen en silver.
- El E2E no re-ejecuta el transform para validar silver (nada tautológico): valida contra los datos.

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

- [ ] Registro de validaciones (`quality/registry.py`): `name`, `layer`, `level`, `description`, `sql`.
- [ ] Implementar las 12 validaciones de `SPECS.md` sobre silver (y 1–3 sobre bronze).
- [ ] La validación 11 con `LAG` (window function) sobre el acumulado mensual.
- [ ] `quality_report.json`: status, conteos, `failed_sample` (≤ 20), `duration_ms` por validación.
- [ ] Gate: cualquier `fail` detiene la construcción de gold; `warn` continúa.
- [ ] Umbrales en `config.py`, no hardcodeados.
- [ ] Crear `ADR-004: registro SQL propio vs pandera/Great Expectations`.

**E2E del checkpoint (el medio-difícil del proyecto):**

- Seed **dirty** → el quality report detecta **12/12** validaciones con `rows_failed` exactos y muestras.
- Seed clean → 12/12 `pass`, 0 warns, 0 cuarentena.
- Con dirty, el pipeline **no construye gold** y el exit code es ≠ 0.
- Los artefactos (`quality_report.json` + checksums) se escriben incluso cuando el gate falla (evidencia).

**Criterio de aceptación:**

- Ninguna validación tautológica ni change-detector.
- Las 12 se listan en el report con su SQL.
- Determinismo: mismas semillas → mismos `rows_failed`.

**Commit sugerido:**

```text
feat: add twelve quality validations
```

---

## Fase 4 — Gold y hallazgos

- [ ] `gold.exec_monthly`: % ejecución por `(entity, category, month)`.
- [ ] `gold.exec_by_entity`: totales y % ejecución anual con `RANK()`/`ROW_NUMBER()`.
- [ ] `gold.findings`: bottom-N municipalidades, categorías críticas, alertas < umbral.
- [ ] `findings.json` como artefacto con lenguaje neutral.
- [ ] Export `execution_by_entity.csv` y `gold_summary.csv` para Power BI.

**E2E del checkpoint:**

- Seed clean → gold con % de ejecución calculado correctamente (el E2E recalcula esperados conocidos del seed y compara).
- Rankings ordenados y con empates resueltos de forma documentada.
- Hallazgos presentes con N municipalidades y categorías.
- Dirty → gold no existe (el gate lo impide).

**Criterio de aceptación:**

- Gold nunca se deriva de bronze.
- Los porcentajes usan `pim_amount` como denominador y manejan PIM = 0.
- El E2E valida matemática de negocio, no solo “hay filas”.

**Commit sugerido:**

```text
feat: add gold aggregations and findings
```

---

## Fase 5 — Volumen, performance y BYOD real

- [ ] Modo `volume` del seed (≥ 1,000,000 filas) para pruebas de performance.
- [ ] Medir duración por etapa (ingest/silver/quality/gold) y registrarlo en `run_manifest.json`.
- [ ] Particionado de Delta por `year`/`month` donde aporte (medido, no adivinado).
- [x] **BYOD descargado (18/11/2026):** 4 archivos oficiales de la Consulta Amigable ya en `data/raw/` (departamentos nacional, municipalidades de Lima, Miraflores mensual, genéricas nacional); procedencia y hashes en `data/raw/README.md`.
- [ ] **BYOD procesado:** run del pipeline sobre los archivos reales → quality report y hallazgos reales.
- [ ] Ajustar el adaptador al formato real (tablas HTML como `.xls`) y documentar el mapping aplicado.
- [ ] Artículo de hallazgos con datos reales (borrador en `docs/`).

**E2E del checkpoint:**

- Volume: pipeline completo en < umbral medido (CI), conteos exactos.
- BYOD real (local): run completo end-to-end con los archivos BYOD reales del usuario, quality report y hallazgos reales.
- El manifest registra el SHA-256 de cada archivo BYOD como procedencia.

**Criterio de aceptación:**

- Duraciones medidas, no estimadas.
- Los hallazgos reales usan lenguaje neutral y citan la fuente y fecha.
- Ningún CSV real se commitea.

**Commit sugerido:**

```text
test: add volume scenario and byod adapter tuning
docs: add real data findings draft
```

---

## Fase 6 — Dashboard, docs y release

- [ ] Dashboard autorado con la skill `powerbi-report-cli` (proyecto PBIP reproducible) y modelo con el MCP `powerbi-modeling`.
- [ ] Capturas del tablero en Power BI Desktop (paso manual del usuario).
- [ ] Notebook wrapper de equivalencia Databricks (≤ 20 líneas, sin lógica).
- [ ] README con capturas y métricas reales.
- [ ] README.en.md.
- [ ] Tag `v0.1.0` y release con artefactos.
- [ ] Actualizar `Portafolio_Proyectos_Peru.md`.

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

## Definición de terminado

Un checkpoint está terminado cuando:

- [ ] El E2E del checkpoint pasa.
- [ ] El artefacto correspondiente existe y es reproducible.
- [ ] El checkbox está marcado.
- [ ] `README.md` está actualizado si cambió algo visible.
- [ ] `ruff format` y `ruff check` pasan.
- [ ] No hay PII, secretos ni datos crudos commiteados.
- [ ] El commit está hecho.

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
