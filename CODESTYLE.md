# CODESTYLE.md — PresupuestoAbiertoPE

> **Regla base:** documentación en español; código, esquema, logs y commits en inglés; `README.en.md` en inglés para reclutadores.

---

## 1. Principios

- **Correctness first:** primero que funcione y sea entendible; después, que sea elegante.
- **Simplicidad:** la abstracción se gana cuando elimina duplicación real, no cuando “se ve profesional”.
- **Explícito sobre implícito:** nombres claros, validaciones nombradas, umbrales en config.
- **Sin magia:** nada de imports dinámicos, `**kwargs` opacos o SQL construido con strings sueltos del usuario.
- **Sin código muerto:** si no se usa, se borra.
- **Sin comentarios narrativos:** el código debe explicarse solo; los comentarios son para decisiones no obvias.
- **Profesionalismo:** no se commitea código roto; no se ocultan fallos; no se adivina un requisito.

---

## 2. Idioma

| Elemento | Idioma |
|---|---|
| Documentación (`SPECS`, `ROADMAP`, `CODESTYLE`, `AGENTS`, `README`) | Español |
| `README.en.md` | Inglés |
| Código, variables, funciones, clases | Inglés |
| Tablas y columnas silver/gold | Inglés |
| Columnas bronze | Español (encabezados originales del CSV del MEF) |
| Logs y errores técnicos | Inglés |
| Commits | Inglés |
| Comentarios técnicos | Inglés, solo si son necesarios |
| Hallazgos y reportes de calidad legibles | Español |

El mapping español → inglés de columnas se define **una vez** en `SPECS.md` y vive como constante en `transforms`.

---

## 3. Stack

- **Python 3.13** (default de la máquina; ver nota).
- **PySpark 4.2.x** (motor local; línea estable actual).
- **delta-spark 4.4.x** (Delta Lake en filesystem).
- **Java 17** (requisito de Spark 4; ya presente en la máquina).
- **pytest** (E2E-first; sin unit tests posteriores al código).
- **ruff** para formato y lint.
- **GitHub Actions** como orquestador de CI.

### Nota sobre Python 3.13 (decisión con evidencia)

Verificado el 18/11/2026 con `pip install --dry-run`: en Python 3.13 resuelven `pyspark-4.2.0` + `delta_spark-4.4.1`. Spark 4.x requiere **Java 17** (ya instalado). Se pinéa 3.13 para usar el Python por defecto de la máquina y la línea estable actual de Spark/Delta, sin mantener un segundo intérprete. Si aparece una incompatibilidad real, se documenta y se decide explícitamente, nunca en silencio.

### Windows local

Spark en Windows necesita `winutils.exe` para operaciones de filesystem. Fase 0 incluye su instalación documentada (`tools/winutils/`, un paso único). **CI (ubuntu) es la validación autoritativa** si aparece cualquier rareza local de Windows.

---

## 4. Estructura

```text
presupuestoabierto/
├─ pyproject.toml
├─ presupuesto/
│  ├─ __init__.py
│  ├─ __main__.py            # CLI: run, validate, seed, summary
│  ├─ config.py              # umbrales, rutas, modos (seed/byod)
│  ├─ shared/
│  │  ├─ spark.py            # ÚNICA creación de sesión Spark + Delta
│  │  ├─ logging.py
│  │  └─ errors.py
│  ├─ ingest/
│  │  ├─ seed.py             # generador sintético determinista
│  │  └─ byod.py             # lector CSV del MEF → bronze
│  ├─ transforms/
│  │  └─ silver.py           # SQL de limpieza, tipos, dedupe, cuarentena
│  ├─ quality/
│  │  ├─ registry.py         # registro de las 12 validaciones
│  │  └─ checks.py           # una función por validación
│  ├─ analytics/
│  │  └─ gold.py             # agregados, % ejecución, rankings, hallazgos
│  ├─ reporting/
│  │  ├─ artifacts.py        # manifest, quality_report, checksums
│  │  └─ exports.py          # CSV de gold para Power BI
│  └─ data/catalogs.py      # catálogos (pliegos, categorías)
├─ data/
│  ├─ raw/                   # BYOD del MEF, HTML-".xls" (gitignored)
│  └─ medallion/             # bronze/silver/gold Delta (gitignored)
├─ notebooks/                # wrappers ≤ 20 líneas (equivalencia Databricks)
├─ dashboard/                # evidencia Power BI (PBIP, capturas)
├─ tests/e2e/
├─ artifacts/e2e/
└─ docs/
```

---

## 5. Reglas de código

- Type hints en todo el código público.
- Funciones pequeñas; una responsabilidad por función.
- Nada de `print()`. Logging JSON estructurado.
- Nada de `except Exception: pass`.
- La sesión Spark se obtiene de `shared.spark`; nada más la crea.
- Spark DataFrames no salen del pipeline: los bordes devuelven conteos, rutas o artefactos.
- **SQL:** strings nombrados en constantes o archivos `.sql`; nunca concatenado con input del usuario.
- **Idempotencia:** toda escritura Delta usa `overwrite` o partición explícita; re-ejecutar no duplica.
- **Umbrales** (`min_rows`, `max_fail_ratio`, `min_month_coverage`) en `config.py`, no hardcodeados.
- **Fechas** en UTC; `year`/`month` derivan del dato presupuestal, no del reloj.
- **Determinismo del seed:** misma semilla → mismo output, byte a byte (para que los checksums del E2E sean estables salvo timestamps declarados).

---

## 6. Reglas de datos

- Bronze: fila cruda + columna de procedencia (`source_file`, `ingested_at`); sin transformar.
- Silver: tipos correctos, claves únicas, catálogos resueltos, cuarentena explícita de filas inválidas.
- Gold: solo agregados derivados de silver validado; nunca de bronze.
- Una validación de nivel `fail` aborta la construcción de gold.
- Toda métrica publicada (README, artículo) debe poder regenerarse con un comando.

---

## 7. Reglas de validaciones (quality)

- Cada validación se registra con: `name`, `layer`, `level` (`fail`/`warn`), `description`, `sql`.
- Cada ejecución produce: `status`, `rows_checked`, `rows_failed`, `failed_sample` (≤ 20 filas), `duration_ms`.
- Las validaciones leen **silver**, no el código interno de los transforms (nada tautológico).
- El quality report es un artefacto con checksum; su estructura se define en `SPECS.md`.
- Prohibido: una validación que re-ejecuta el transform y compara consigo mismo (tautológico) o que solo verifica que cambió algo (change-detector).

---

## 8. Testing

- **E2E-first:** el escenario se escribe antes de la implementación.
- **Sin unit tests después del código.**
- Si necesitas aislar un sistema, primero enumera sus modos de fallo y luego implementa.
- Escenario medio-difícil: seed sucio con una violación por validación; el E2E exige 12/12 detectadas con conteos exactos.
- Artefactos repetibles en `artifacts/e2e/` con `checksums.sha256`.
- Nunca se llama al MEF desde tests ni CI.

### Nombres de tests

```text
test_e2e_clean_seed_produces_gold_and_findings
test_e2e_dirty_seed_detects_all_twelve_validations
test_e2e_byod_contract_matches_mef_columns
test_e2e_quality_gate_blocks_gold_on_fail_level
test_e2e_pipeline_is_idempotent_on_rerun
```

---

## 9. Git

### Commits

```text
feat: add bronze ingestion and seed generator
fix: handle null months in silver transforms
docs: add quality report specification
test: add dirty fixture e2e scenario
refactor: isolate validation registry
chore: release v0.1.0
```

- Un commit por checkpoint significativo.
- Mensaje en inglés, imperativo, corto.
- No commitear `data/raw/`, `data/medallion/`, artefactos sin checksum ni binarios grandes (winutils se documenta, no se commitea si pesa > 1 MB; se provee script de descarga).

### Ramas

- `main` estable.
- `feat/<short-name>` para features.
- No trabajar directo en `main` si hay más de una persona.

---

## 10. Formato

```powershell
python -m ruff format .
python -m ruff check .
```

Configuración en `pyproject.toml`:

- `line-length = 100`
- `target-version = "py313"`
- Reglas: `E`, `F`, `I`, `UP`, `B`, `SIM`.

---

## 11. Comentarios

Permitidos:

- Decisiones no obvias (“silver cuarentena antes de dedupe para no perder evidencia de filas malas”).
- Workarounds con referencia al issue.
- Invariantes de negocio (“devengado es acumulado mensual en la Consulta Amigable”).

Prohibidos:

- “Carga el CSV”.
- Código comentado.
- TODOs sin dueño ni fecha.

---

## 12. Anti-patrones

- Un dios-script de 1,000 líneas que hace todo.
- SQL duplicado entre silver y validaciones.
- Lógica de negocio en notebooks.
- Umbrales mágicos dispersos.
- Validaciones tautológicas o change-detector.
- Commitear archivos BYOD reales.
- Métricas de performance inventadas (si no se midió, no se reporta).
- “Funciona en mi máquina” sin CI que lo pruebe.
