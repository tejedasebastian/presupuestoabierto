"""Gold layer: aggregations from validated silver, findings and the gate.

Gold is only built when the quality gate passes. Execution percentages are
recomputed from silver amounts (never trusted from the export's own
Avance %), and rankings use window functions.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

FINDINGS_BOTTOM_N = 10


def gold_dir(medallion_dir: Path) -> Path:
    return medallion_dir / "gold"


def build_exec_by_entity(silver: DataFrame) -> DataFrame:
    """Per-entity annual totals with department, execution pct and national rank."""
    annual = silver.filter(F.col("grain") == "entity_annual").select(
        "entity_code", "entity_name", "department", "department_code", "pim", "accrued"
    )
    window = Window.orderBy(F.col("execution_pct").desc(), F.col("entity_code"))
    return (
        annual.groupBy("entity_code", "entity_name", "department", "department_code")
        .agg(
            F.sum("pim").alias("pim_total"),
            F.sum("accrued").alias("accrued_total"),
        )
        .withColumn(
            "execution_pct",
            F.when(
                F.col("pim_total") > 0, F.col("accrued_total") / F.col("pim_total") * 100
            ).otherwise(0.0),
        )
        .withColumn("rank", F.row_number().over(window))
    )


def build_exec_monthly(silver: DataFrame) -> DataFrame:
    return silver.filter(F.col("grain") == "entity_monthly").select(
        "entity_code", "entity_name", "month", "accrued", "paid"
    )


def _pct_rows(silver: DataFrame, grain: str) -> list[dict]:
    rows = (
        silver.filter(F.col("grain") == grain)
        .select("category", "category_code", "department", "department_code", "pim", "accrued")
        .collect()
    )
    out = []
    for row in rows:
        pim = float(row["pim"] or 0)
        accrued = float(row["accrued"] or 0)
        out.append(
            {
                "label": row["category"] or row["department"],
                "code": row["category_code"] or row["department_code"],
                "pim": pim,
                "accrued": accrued,
                "execution_pct": round(accrued / pim * 100, 1) if pim else 0.0,
            }
        )
    return sorted(out, key=lambda item: item["execution_pct"])


def build_findings(
    exec_by_entity: DataFrame,
    silver: DataFrame,
    low_threshold: float,
) -> dict:
    rows = exec_by_entity.collect()
    ordered = sorted(rows, key=lambda row: row["execution_pct"])
    bottom = ordered[:FINDINGS_BOTTOM_N]
    alerts = [row for row in rows if row["execution_pct"] < low_threshold]

    def entity_brief(row) -> dict:
        return {
            "entity_code": row["entity_code"],
            "entity_name": row["entity_name"],
            "department": row["department"],
            "department_code": row["department_code"],
            "pim_total": float(row["pim_total"] or 0),
            "accrued_total": float(row["accrued_total"] or 0),
            "execution_pct": round(row["execution_pct"], 1),
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "bottom_n": [entity_brief(row) for row in bottom],
        "low_execution_alerts": sorted(
            (entity_brief(row) for row in alerts),
            key=lambda item: item["execution_pct"],
        ),
        "categories": _pct_rows(silver, "category_national"),
        "departments": _pct_rows(silver, "department"),
        "note": "Findings describe budget execution, not intentions.",
    }


def write_gold(
    spark: SparkSession,
    silver: DataFrame,
    medallion_dir: Path,
    low_threshold: float,
) -> dict:
    """Build and persist all gold tables; return findings + exports."""
    out = gold_dir(medallion_dir)
    out.mkdir(parents=True, exist_ok=True)

    exec_by_entity = build_exec_by_entity(silver)
    exec_monthly = build_exec_monthly(silver)
    exec_by_entity.write.format("delta").option("overwriteSchema", "true").mode("overwrite").save(
        str(out / "exec_by_entity")
    )
    exec_monthly.write.format("delta").option("overwriteSchema", "true").mode("overwrite").save(
        str(out / "exec_monthly")
    )

    findings = build_findings(exec_by_entity, silver, low_threshold)
    return {
        "entities": exec_by_entity.count(),
        "monthly_rows": exec_monthly.count(),
        "findings": findings,
        "exec_by_entity": exec_by_entity,
    }


def remove_gold(medallion_dir: Path) -> None:
    """Gate blocked: stale gold would misrepresent the current dataset."""
    out = gold_dir(medallion_dir)
    if out.exists():
        shutil.rmtree(out)


def write_findings(findings: dict, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / "findings.json"
    path.write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return path
