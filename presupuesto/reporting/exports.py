"""Power BI exports from gold: CSV artifacts with stable headers."""

from __future__ import annotations

import csv
from pathlib import Path

from pyspark.sql import DataFrame

EXEC_BY_ENTITY_HEADER = [
    "entity_code",
    "entity_name",
    "pim_total",
    "accrued_total",
    "execution_pct",
    "rank",
]

GOLD_SUMMARY_HEADER = ["metric", "value"]

FINDINGS_CSV_HEADER = ["label", "code", "pim", "accrued", "execution_pct"]


def _write_findings_csv(items: list[dict], path: Path) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FINDINGS_CSV_HEADER)
        for item in items:
            writer.writerow(
                [item["label"], item["code"], item["pim"], item["accrued"], item["execution_pct"]]
            )
    return path


def write_category_csv(findings: dict, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return _write_findings_csv(findings["categories"], artifacts_dir / "category_summary.csv")


def write_department_csv(findings: dict, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return _write_findings_csv(findings["departments"], artifacts_dir / "department_summary.csv")


def write_exec_by_entity_csv(df: DataFrame, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / "execution_by_entity.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EXEC_BY_ENTITY_HEADER)
        for row in df.orderBy("rank").collect():
            writer.writerow(
                [
                    row["entity_code"],
                    row["entity_name"],
                    row["pim_total"],
                    row["accrued_total"],
                    row["execution_pct"],
                    row["rank"],
                ]
            )
    return path


def write_gold_summary_csv(
    df: DataFrame,
    findings: dict,
    artifacts_dir: Path,
) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / "gold_summary.csv"
    rows = df.collect()
    pcts = [row["execution_pct"] for row in rows]
    summary = {
        "entities": len(rows),
        "avg_execution_pct": round(sum(pcts) / len(pcts), 1) if pcts else 0.0,
        "best_execution_pct": round(max(pcts), 1) if pcts else 0.0,
        "worst_execution_pct": round(min(pcts), 1) if pcts else 0.0,
        "low_execution_alerts": len(findings["low_execution_alerts"]),
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(GOLD_SUMMARY_HEADER)
        for key, value in summary.items():
            writer.writerow([key, value])
    return path
