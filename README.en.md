# PresupuestoAbiertoPE

**Open data pipeline with quality gates and cloud-ready design.**

PresupuestoAbiertoPE turns municipal budget execution (official exports from Peru's Ministry of Economy) into a **bronze → silver → gold** medallion with **12 quality validations**, and answers a simple question: which municipalities execute the least, in which categories, and in which months?

> **Status:** v0.1.0 in development. This README describes the finished product; screenshots and metrics will be completed as the roadmap closes.
>
> **Español:** [README.md](README.md)

---

## Why PresupuestoAbiertoPE?

Municipal budget execution data is scattered and hard to compare. The Ministry's "Consulta Amigable" lets you query one entity at a time, but not all of them side by side. Citizens, journalists, and local governments lack a simple board to spot low execution or priorities.

PresupuestoAbiertoPE answers:

- What percentage of its budget (PIM) did each municipality execute?
- Which categories have the lowest execution?
- Which months concentrate the slowdown?
- Which entities show sustained low execution?

---

## What it does

1. **BYOD:** you download the official export (HTML-`.xls`) from the Ministry's Consulta Amigable with your browser.
2. **Bronze:** the pipeline ingests it raw with provenance and a per-row hash.
3. **Silver:** typing, dedupe, catalog resolution, and explicit quarantine.
4. **Quality:** 12 validations with a gate; any `fail` blocks gold.
5. **Gold:** execution percentage by municipality, category, and month, with rankings (window functions).
6. **Findings:** bottom-N execution, critical categories, and alerts.
7. **Dashboard:** CSV exports ready for Power BI with a reproducible spec.

It does not scrape the Ministry, does not invent findings, and does not accuse anyone: it describes budget execution in neutral language.

---

## Demo

> Screenshots pending implementation.

![Medallion pipeline](docs/assets/pipeline.png)

![Quality report](docs/assets/quality.png)

![Power BI dashboard](docs/assets/dashboard.png)

---

## Architecture

```text
Official BYOD exports (human browser) → data/raw/*.xls
        │
        ▼
     ingest ──► BRONZE (Delta, raw rows + provenance)
        │
        ▼
    transform ──► SILVER (Delta, types + dedupe + catalogs + quarantine)
        │
        ▼
     quality ──► 12 SQL validations → quality_report.json (gate)
        │
        ▼ (only if the gate passes)
    analytics ──► GOLD (Delta, execution % + rankings + findings)
        │
        ▼
    reporting ──► artifacts/e2e/ + CSV exports + dashboard/
```

**Contexts:** `ingest`, `transform`, `quality`, `analytics`, `reporting`, `shared`.

**Rules:**

- The Spark session is created in exactly one place.
- Business SQL lives in `transforms`/`analytics`, never in notebooks or the CLI.
- Validations read silver with their own SQL; nothing tautological.
- The pipeline is idempotent: reruns never duplicate data.
- BYOD files are never committed; the manifest records their SHA-256.

---

## Stack

| Layer | Technology |
|---|---|
| Engine | Apache Spark (PySpark), local |
| Format | Delta Lake (pip: `delta-spark`) |
| Language | Python 3.13 + PySpark 4.2 + Delta 4.4 (verified with `pip --dry-run`) |
| Requirement | Java 17 |
| Quality | 12 SQL validations with an in-house registry and gate |
| Dashboard | Power BI (CSV exports + reproducible spec) |
| Testing | pytest, E2E-first, artifacts with checksums |
| CI | GitHub Actions (Java 17 + Python 3.13) |

**Documented equivalences:** Databricks (wrapper notebook), Prefect (scheduled orchestration), MinIO (storage). None are MVP dependencies.

---

## The 12 validations

| # | Name | Level | What it checks |
|---|---|---|---|
| 1 | `raw_schema_present` | fail | Required columns in the export |
| 2 | `raw_row_count` | fail | Minimum row count |
| 3 | `raw_parseable` | warn | % of parseable numerics |
| 4 | `silver_types` | fail | Types: year, month 1–12, amounts |
| 5 | `silver_no_null_keys` | fail | Key without nulls |
| 6 | `silver_unique_keys` | fail | No duplicates |
| 7 | `silver_catalog_referential` | fail | Entity codes in catalog |
| 8 | `silver_entity_named` | warn | Entity not a placeholder |
| 9 | `business_devengado_le_pim` | fail | Accrued ≤ PIM |
| 10 | `business_amounts_positive` | fail | Amounts ≥ 0 |
| 11 | `business_cumulative_monotonic` | warn | Cumulative non-decreasing (`LAG`) |
| 12 | `business_coverage_months` | warn | Month coverage |

A `fail` blocks gold; a `warn` is reported. Everything lands in `quality_report.json` with counts and samples.

---

## Quick start

> Requirements: Java 17, Python 3.13, ~2 GB of free RAM (close Docker if needed). On Windows, install `winutils.exe` once (documented in Phase 0).

```powershell
git clone <repository-url>
cd presupuestoabierto

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Reproducible demo with the synthetic seed
python -m presupuesto run --source seed --mode clean

# Quality gate demo (12 detected violations)
python -m presupuesto run --source seed --mode dirty

# Your real data from the Ministry
python -m presupuesto run --source byod --file data/raw/consulta_amigable_lima_municipalidades_2025.xls
```

Every run writes checksummed artifacts to `artifacts/e2e/`.

---

## Testing

- E2E-first; no unit tests after the code.
- Medium-hard scenario: the dirty seed injects one violation per validation and the E2E demands **12/12 detected** with exact counts.
- CI (GitHub Actions) reproduces everything with the synthetic seed; it never calls the Ministry.

```powershell
pytest tests/e2e -v
```

Artifacts:

```text
artifacts/e2e/
├─ run_manifest.json
├─ quality_report.json
├─ findings.json
├─ execution_by_entity.csv
├─ gold_summary.csv
└─ checksums.sha256
```

---

## Metrics

> Completed with E2E and real BYOD data. No invented numbers.

| Metric | Value |
|---|---|
| Records processed (real BYOD) | 218 |
| Municipalities covered (Lima dept.) | 171 |
| Quality score (real BYOD) | **12/12 pass** |
| Pipeline runtime (real BYOD, local) | 112.9 s |
| Average execution | 84.7% |
| Findings from real data | 9 alerts < 60%; worst: Colonia 21.8% |
| Volume (CI) | 12,800 entities ≈ 934k rows |

---

## Limitations

- v0.1 processes a single year and expenses only.
- No scraping: data arrives BYOD from your browser.
- The Ministry's export format may vary; the adapter fails explicitly when columns are missing.
- Findings describe execution, not causes.
- The final `.pbix` is assembled in Power BI Desktop (manual).
- The dashboard is not published to Power BI Service in v0.1.

---

## Roadmap

- v0.1: BYOD ingestion, medallion, 12 validations, gold, findings, dashboard evidence, release.
- v0.2: MinIO, Prefect, multi-year, revenue data, SEACE comparison, dashboard publishing.

See [ROADMAP.md](ROADMAP.md).

---

## License

MIT for the code. Ministry data keeps its own terms; this project is not affiliated.

---

## Credits

- Source: [MEF — Consulta Amigable (budget execution)](https://www.mef.gob.pe/). Manual download by the user (BYOD).
- Built as a portfolio project for data engineering and BI roles.
