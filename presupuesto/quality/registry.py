"""The twelve quality validations (SPECS section 9) with the gold gate.

Semantics:
- level "fail" + status "fail" blocks gold (the gate).
- level "warn" never blocks; status is "warn" when rows_failed > 0.
- File-level checks (1, 2) consume the ingest failures collected per file.
- Row-level checks run over silver with their own SQL; none of them
  re-executes a transform (nothing tautological).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

SAMPLE_LIMIT = 20
# Spark 4 rejects list literals via .isin(container); use explicit filters.
_PLACEHOLDERS = ("SIN DATO", "N/D", "-")


def _is_entity_grain():
    return (F.col("grain") == "entity_annual") | (F.col("grain") == "entity_monthly")


@dataclass(slots=True)
class CheckResult:
    name: str
    layer: str
    level: str
    status: str
    rows_checked: int
    rows_failed: int
    duration_ms: float
    sql: str
    failed_sample: list[dict] = field(default_factory=list)


def _finish(
    name: str,
    layer: str,
    level: str,
    rows_checked: int,
    rows_failed: int,
    duration_ms: float,
    sql: str,
    sample_df: DataFrame | None = None,
) -> CheckResult:
    sample: list[dict] = []
    if sample_df is not None and rows_failed > 0:
        sample = [
            {key: row[key] for key in row.asDict() if key != "ingested_at"}
            for row in sample_df.limit(SAMPLE_LIMIT).collect()
        ]
    status = "pass" if rows_failed == 0 else "fail" if level == "fail" else "warn"
    return CheckResult(
        name=name,
        layer=layer,
        level=level,
        status=status,
        rows_checked=rows_checked,
        rows_failed=rows_failed,
        duration_ms=duration_ms,
        sql=sql,
        failed_sample=sample,
    )


def check_raw_schema_present(files_attempted: int, file_failures: list[dict]) -> CheckResult:
    started = time.perf_counter()
    failed = [f for f in file_failures if f["details"].get("check") == "raw_schema_present"]
    return CheckResult(
        name="raw_schema_present",
        layer="file",
        level="fail",
        status="fail" if failed else "pass",
        rows_checked=files_attempted,
        rows_failed=len(failed),
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql="MapTable labels must contain PIA, PIM, DEVENGADO, GIRADO per export",
        failed_sample=failed,
    )


def check_raw_row_count(files_attempted: int, file_failures: list[dict]) -> CheckResult:
    started = time.perf_counter()
    failed = [f for f in file_failures if f["details"].get("check") == "raw_row_count"]
    return CheckResult(
        name="raw_row_count",
        layer="file",
        level="fail",
        status="fail" if failed else "pass",
        rows_checked=files_attempted,
        rows_failed=len(failed),
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql=(
            "entity_monthly exports must carry >= settings.min_rows rows; "
            "entity_annual exports may be small"
        ),
        failed_sample=failed,
    )


def check_raw_parseable(silver: DataFrame, annual_count: int, max_ratio: float) -> CheckResult:
    started = time.perf_counter()
    condition = (F.col("grain") == "entity_annual") & F.col("pim").isNull()
    bad = silver.filter(condition)
    rows_failed = bad.count()
    ratio = (rows_failed / annual_count) if annual_count else 0.0
    status = "pass" if rows_failed == 0 else ("fail" if ratio > max_ratio else "warn")
    sample = (
        [
            {key: row[key] for key in ("row_hash", "entity_name", "pim", "source_file")}
            for row in bad.limit(SAMPLE_LIMIT).collect()
        ]
        if rows_failed
        else []
    )
    return CheckResult(
        name="raw_parseable",
        layer="bronze",
        level="warn",
        status=status,
        rows_checked=annual_count,
        rows_failed=rows_failed,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql="grain = 'entity_annual' AND pim IS NULL (parse errors survive as NULL amounts)",
        failed_sample=sample,
    )


def check_silver_types(silver: DataFrame) -> CheckResult:
    started = time.perf_counter()
    condition = F.col("month").isNotNull() & ~F.col("month").between(1, 12)
    bad = silver.filter(condition)
    rows_failed = bad.count()
    return _finish(
        "silver_types",
        "silver",
        "fail",
        silver.count(),
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        "month IS NOT NULL AND month NOT BETWEEN 1 AND 12",
        bad.select("row_hash", "entity_code", "month", "source_file"),
    )


def check_silver_no_null_keys(silver: DataFrame, entity_rows: int) -> CheckResult:
    started = time.perf_counter()
    condition = _is_entity_grain() & F.col("entity_code").isNull()
    bad = silver.filter(condition)
    rows_failed = bad.count()
    return _finish(
        "silver_no_null_keys",
        "silver",
        "fail",
        entity_rows,
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        "grain IN ('entity_annual','entity_monthly') AND entity_code IS NULL",
        bad.select("row_hash", "grain", "entity_ubigee", "entity_name", "source_file"),
    )


def check_silver_unique_keys(silver: DataFrame) -> CheckResult:
    started = time.perf_counter()
    grouped = silver.groupBy(
        "grain",
        "year",
        F.coalesce(F.col("month"), F.lit(-1)).alias("month"),
        F.coalesce(F.col("entity_code"), F.lit("")).alias("entity_code"),
        F.coalesce(F.col("category_code"), F.lit("")).alias("category_code"),
        F.coalesce(F.col("department_code"), F.lit("")).alias("department_code"),
    ).count()
    duplicated = grouped.filter(F.col("count") > 1)
    dup_rows = duplicated.collect()
    rows_failed = sum(row["count"] - 1 for row in dup_rows)
    sql = (
        "GROUP BY grain, year, coalesce(month,-1), coalesce(entity_code,''), "
        "coalesce(category_code,''), coalesce(department_code,'') HAVING count(*) > 1"
    )
    return CheckResult(
        name="silver_unique_keys",
        layer="silver",
        level="fail",
        status="fail" if rows_failed else "pass",
        rows_checked=silver.count(),
        rows_failed=rows_failed,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql=sql,
        failed_sample=[
            {
                "grain": row["grain"],
                "year": row["year"],
                "entity_code": row["entity_code"],
                "count": row["count"],
            }
            for row in dup_rows[:SAMPLE_LIMIT]
        ],
    )


def check_silver_catalog_referential(silver: DataFrame, monthly_rows: int) -> CheckResult:
    started = time.perf_counter()
    monthly = silver.filter(F.col("grain") == "entity_monthly")
    annual_codes = silver.filter(F.col("grain") == "entity_annual").select("entity_code").distinct()
    # left_anti join: monthly rows whose entity has no annual row. Robust in
    # Spark 4 (no collection literals) and scales to any catalog size.
    bad = monthly.join(annual_codes, on="entity_code", how="left_anti")
    rows_failed = bad.count()
    return _finish(
        "silver_catalog_referential",
        "silver",
        "fail",
        monthly_rows,
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        "SELECT m.* FROM silver m WHERE m.grain='entity_monthly' LEFT ANTI JOIN "
        "(SELECT DISTINCT entity_code FROM silver WHERE grain='entity_annual') a "
        "ON m.entity_code = a.entity_code",
        bad.select("row_hash", "entity_code", "entity_name", "month", "source_file"),
    )


def check_silver_entity_named(silver: DataFrame, entity_rows: int) -> CheckResult:
    started = time.perf_counter()
    condition = _is_entity_grain() & (
        F.col("entity_name").isNull()
        | (F.upper(F.coalesce(F.col("entity_name"), F.lit(""))) == F.lit(""))
        | F.upper(F.coalesce(F.col("entity_name"), F.lit(""))).isin(*_PLACEHOLDERS)
    )
    bad = silver.filter(condition)
    rows_failed = bad.count()
    return _finish(
        "silver_entity_named",
        "silver",
        "warn",
        entity_rows,
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        "grain IN entity grains AND (entity_name IS NULL OR UPPER(entity_name) IN placeholders)",
        bad.select("row_hash", "entity_code", "entity_name", "source_file"),
    )


def check_business_devengado_le_pim(silver: DataFrame) -> CheckResult:
    started = time.perf_counter()
    condition = F.col("pim").isNotNull() & (F.col("pim") > 0) & (F.col("accrued") > F.col("pim"))
    bad = silver.filter(condition)
    rows_failed = bad.count()
    return _finish(
        "business_devengado_le_pim",
        "silver",
        "fail",
        silver.filter(F.col("pim").isNotNull()).count(),
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        "pim IS NOT NULL AND pim > 0 AND accrued > pim (negative PIM belongs to check 10)",
        bad.select("row_hash", "entity_code", "pim", "accrued", "source_file"),
    )


AMOUNT_COLUMNS = [
    "pia",
    "pim",
    "certification",
    "annual_commitment",
    "monthly_commitment",
    "accrued",
    "paid",
]


def check_business_amounts_positive(silver: DataFrame) -> CheckResult:
    started = time.perf_counter()
    negative = F.lit(False)
    for column in AMOUNT_COLUMNS:
        negative = negative | (F.col(column) < 0)
    bad = silver.filter(negative)
    rows_failed = bad.count()
    columns_sql = ", ".join(AMOUNT_COLUMNS)
    return _finish(
        "business_amounts_positive",
        "silver",
        "fail",
        silver.count(),
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        f"any of ({columns_sql}) < 0",
        bad.select("row_hash", "entity_code", "pim", "accrued", "source_file"),
    )


def check_business_monthly_sums_to_annual(silver: DataFrame, tolerance: float) -> CheckResult:
    started = time.perf_counter()
    monthly = (
        silver.filter(F.col("grain") == "entity_monthly")
        .groupBy("entity_code")
        .agg(F.sum("accrued").alias("monthly_sum"))
    )
    annual = silver.filter(F.col("grain") == "entity_annual").select(
        "entity_code", F.col("accrued").alias("annual_accrued")
    )
    # One annual row per entity: duplicates are already flagged by check 6;
    # deduplicating keeps this check's semantics well-defined.
    annual = annual.dropDuplicates(["entity_code"])
    joined = monthly.join(annual, on="entity_code", how="inner")
    bad = joined.filter(
        F.abs(F.col("monthly_sum") - F.col("annual_accrued"))
        > F.abs(F.col("annual_accrued")) * F.lit(tolerance)
    )
    rows_failed = bad.count()
    return _finish(
        "business_monthly_sums_to_annual",
        "silver",
        "warn",
        joined.count(),
        rows_failed,
        round((time.perf_counter() - started) * 1000, 2),
        f"|SUM(monthly.accrued) - annual.accrued| > |annual.accrued| * {tolerance} "
        "GROUP BY entity_code (entities with both grains)",
        bad.select("entity_code", "monthly_sum", "annual_accrued"),
    )


def check_business_coverage_months(silver: DataFrame, min_months: int) -> CheckResult:
    started = time.perf_counter()
    coverage = (
        silver.filter(F.col("grain") == "entity_monthly")
        .groupBy("entity_code")
        .agg(F.countDistinct("month").alias("months"))
    )
    bad = coverage.filter(F.col("months") < min_months)
    bad_rows = bad.collect()
    rows_failed = len(bad_rows)
    return CheckResult(
        name="business_coverage_months",
        layer="silver",
        level="warn",
        status="warn" if rows_failed else "pass",
        rows_checked=coverage.count(),
        rows_failed=rows_failed,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql=(
            f"COUNT(DISTINCT month) GROUP BY entity_code (entity_monthly) "
            f"HAVING months < {min_months}"
        ),
        failed_sample=[row.asDict() for row in bad_rows[:SAMPLE_LIMIT]],
    )


def run_quality(
    silver: DataFrame,
    file_failures: list[dict],
    files_attempted: int,
    settings,
) -> dict:
    """Run the 12 checks, build the report and evaluate the gate."""
    total_rows = silver.count()
    entity_rows = silver.filter(_is_entity_grain()).count()
    annual_count = silver.filter(F.col("grain") == "entity_annual").count()
    monthly_rows = silver.filter(F.col("grain") == "entity_monthly").count()

    checks = [
        check_raw_schema_present(files_attempted, file_failures),
        check_raw_row_count(files_attempted, file_failures),
        check_raw_parseable(silver, annual_count, settings.max_parse_error_ratio),
        check_silver_types(silver),
        check_silver_no_null_keys(silver, entity_rows),
        check_silver_unique_keys(silver),
        check_silver_catalog_referential(silver, monthly_rows),
        check_silver_entity_named(silver, entity_rows),
        check_business_devengado_le_pim(silver),
        check_business_amounts_positive(silver),
        check_business_monthly_sums_to_annual(silver, settings.monthly_annual_tolerance),
        check_business_coverage_months(silver, settings.min_month_coverage),
    ]

    blocking = [c.name for c in checks if c.level == "fail" and c.status == "fail"]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows_checked_total": total_rows,
        "checks": [
            {
                "name": c.name,
                "layer": c.layer,
                "level": c.level,
                "status": c.status,
                "rows_checked": c.rows_checked,
                "rows_failed": c.rows_failed,
                "duration_ms": c.duration_ms,
                "sql": c.sql,
                "failed_sample": c.failed_sample,
            }
            for c in checks
        ],
        "summary": {
            "total_checks": len(checks),
            "failed_checks": sum(1 for c in checks if c.status == "fail"),
            "warn_checks": sum(1 for c in checks if c.status == "warn"),
            "passed_checks": sum(1 for c in checks if c.status == "pass"),
        },
        "gate": {
            "blocked": bool(blocking),
            "blocking_checks": blocking,
            "rule": "any level=fail check with status=fail blocks gold",
        },
    }
    return report


def write_quality_report(report: dict, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / "quality_report.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path
