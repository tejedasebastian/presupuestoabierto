"""Silver transform: grain-aware typed canonical rows + structural quarantine.

Division of labor (SPECS 8.2):
- Quarantine: rows with null accrued (execution cannot be measured). Structural
  dead weight, never silently dropped, always reported.
- Business violations (month 13, duplicates, null keys, negative amounts...)
  stay in silver: the quality registry detects them and the gate decides.
"""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

AMOUNT_COLUMNS = [
    "pia",
    "pim",
    "certification",
    "annual_commitment",
    "monthly_commitment",
    "accrued",
    "paid",
]

SILVER_COLUMNS = [
    "grain",
    "entity_ubigee",
    "entity_code",
    "entity_name",
    "year",
    "month",
    "category",
    "category_code",
    "department",
    "department_code",
    *AMOUNT_COLUMNS,
    "execution_pct",
    "query_date",
    "source_file",
    "ingested_at",
    "row_hash",
    "concept_raw",
]


def silver_paths(medallion_dir: Path) -> tuple[Path, Path]:
    base = medallion_dir / "silver"
    return base / "budget_execution", base / "budget_execution_quarantine"


def build_silver(spark: SparkSession, bronze: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Split bronze into typed silver and structural quarantine.

    Silver keeps the amount columns cast to decimal(18,2); quarantine keeps
    the raw values plus the reason.
    """
    quarantine_rows = bronze.filter(bronze.accrued.isNull()).withColumn(
        "quarantine_reason", F.lit("null_accrued")
    )

    typed = bronze.filter(bronze.accrued.isNotNull())
    for column in AMOUNT_COLUMNS:
        typed = typed.withColumn(column, F.col(column).cast("decimal(18,2)"))
    typed = typed.withColumn("execution_pct", F.col("execution_pct").cast("double"))
    typed = typed.select(*SILVER_COLUMNS)

    return typed, quarantine_rows


def write_silver(
    silver: DataFrame,
    quarantine: DataFrame,
    medallion_dir: Path,
) -> tuple[Path, Path]:
    silver_path, quarantine_path = silver_paths(medallion_dir)
    silver.write.format("delta").mode("overwrite").save(str(silver_path))
    quarantine.write.format("delta").mode("overwrite").save(str(quarantine_path))
    return silver_path, quarantine_path
