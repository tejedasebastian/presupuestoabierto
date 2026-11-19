"""Bronze Delta writer: canonical rows -> idempotent Delta table."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

CANONICAL_FIELDS = [
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
    "pia",
    "pim",
    "certification",
    "annual_commitment",
    "monthly_commitment",
    "accrued",
    "paid",
    "execution_pct",
    "query_date",
    "source_file",
    "concept_raw",
]

SCHEMA = StructType(
    [
        StructField("grain", StringType(), False),
        StructField("entity_ubigee", StringType(), True),
        StructField("entity_code", StringType(), True),
        StructField("entity_name", StringType(), True),
        StructField("year", IntegerType(), False),
        StructField("month", IntegerType(), True),
        StructField("category", StringType(), True),
        StructField("category_code", StringType(), True),
        StructField("department", StringType(), True),
        StructField("department_code", StringType(), True),
        StructField("pia", DoubleType(), True),
        StructField("pim", DoubleType(), True),
        StructField("certification", DoubleType(), True),
        StructField("annual_commitment", DoubleType(), True),
        StructField("monthly_commitment", DoubleType(), True),
        StructField("accrued", DoubleType(), True),
        StructField("paid", DoubleType(), True),
        StructField("execution_pct", DoubleType(), True),
        StructField("query_date", StringType(), True),
        StructField("source_file", StringType(), False),
        StructField("ingested_at", TimestampType(), False),
        StructField("row_hash", StringType(), False),
        StructField("concept_raw", StringType(), True),
    ]
)


def _row_hash(row: dict) -> str:
    canonical = "|".join(str(row.get(field)) for field in CANONICAL_FIELDS)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def bronze_path(medallion_dir: Path) -> Path:
    return medallion_dir / "bronze" / "budget_execution"


def write_bronze(
    spark: SparkSession,
    rows: list[dict],
    medallion_dir: Path,
) -> Path:
    """Overwrite bronze with the given rows (idempotent per source set)."""
    ingested_at = datetime.now(UTC)
    payload = []
    for row in rows:
        enriched = {field: row.get(field) for field in CANONICAL_FIELDS}
        enriched["ingested_at"] = ingested_at
        enriched["row_hash"] = _row_hash(row)
        payload.append(enriched)

    df = spark.createDataFrame(payload, schema=SCHEMA)
    out = bronze_path(medallion_dir)
    df.write.format("delta").mode("overwrite").save(str(out))
    return out
