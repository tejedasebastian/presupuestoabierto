"""E2E for Fase 4: gold aggregations, findings and Power BI exports.

Gold is built ONLY when the quality gate passes. The E2E recomputes the
expected execution percentages from the seed formula instead of trusting
the pipeline's own math (no tautology), and verifies the gate blocks gold
on the dirty run.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "artifacts" / "e2e"


def _entity_amounts(index: int) -> dict:
    """Mirror of the seed formula (independent recomputation for the E2E)."""
    base = 1_000_000 + index * 123_457
    pim = int(base * 1.08)
    pct = 0.57 + (index % 7) * 0.065
    accrued = int(pim * pct)
    return {"pim": pim, "accrued": accrued, "pct": accrued / pim * 100}


def _gold_paths():
    from presupuesto.config import get_settings

    settings = get_settings()
    gold = settings.medallion_dir / "gold"
    return settings, gold


def test_clean_seed_builds_gold_with_math(spark_session) -> None:
    from presupuesto.pipeline import run_seed

    settings, gold = _gold_paths()
    run_seed(settings, mode="clean")

    by_entity = spark_session.read.format("delta").load(str(gold / "exec_by_entity"))
    rows = by_entity.collect()
    assert len(rows) == 50

    by_code = {row["entity_code"]: row for row in rows}
    # Entity index 0 -> pliego 301001; index 9 -> 301010.
    for index, code in ((0, "301001"), (9, "301010"), (49, "301050")):
        expected = _entity_amounts(index)
        row = by_code[code]
        assert float(row["pim_total"]) == expected["pim"]
        assert float(row["accrued_total"]) == expected["accrued"]
        assert abs(row["execution_pct"] - expected["pct"]) < 0.01

    # Rank is a dense 1..50 window over execution_pct.
    ranks = sorted(row["rank"] for row in rows)
    assert ranks == list(range(1, 51))
    best = min(rows, key=lambda row: row["rank"])
    worst = max(rows, key=lambda row: row["rank"])
    assert best["execution_pct"] > worst["execution_pct"]

    monthly = spark_session.read.format("delta").load(str(gold / "exec_monthly"))
    assert monthly.count() == 24  # 2 entities x 12 months
    months = {row["month"] for row in monthly.collect()}
    assert months == set(range(1, 13))


def test_findings_and_exports_written(spark_session) -> None:
    from presupuesto.pipeline import run_seed

    settings, _ = _gold_paths()
    summary = run_seed(settings, mode="clean")

    findings_path = ARTIFACTS / "findings.json"
    assert findings_path.exists()
    findings = json.loads(findings_path.read_text(encoding="utf-8"))

    assert findings["bottom_n"], "findings must list the lowest executors"
    assert len(findings["bottom_n"]) <= 10
    # The seed's formula puts entities with pct 0.57 (index % 7 == 0) below
    # the 60% alert threshold: indexes 0,7,14,21,28,35,42,49 -> 8 alerts.
    assert len(findings["low_execution_alerts"]) == 8
    assert findings["categories"], "national category findings must be present"
    assert findings["departments"]

    # Power BI exports.
    by_entity_csv = ARTIFACTS / "execution_by_entity.csv"
    assert by_entity_csv.exists()
    lines = by_entity_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 51  # header + 50 entities
    assert lines[0] == "entity_code,entity_name,pim_total,accrued_total,execution_pct,rank"

    summary_csv = ARTIFACTS / "gold_summary.csv"
    assert summary_csv.exists()

    assert summary["gold"]["blocked"] is False
    assert summary["gold"]["entities"] == 50


def test_dirty_seed_blocks_gold(spark_session) -> None:
    """The gate must block gold and remove any stale gold from clean runs."""
    from presupuesto.pipeline import run_seed

    settings, gold = _gold_paths()
    run_seed(settings, mode="clean")
    assert (gold / "exec_by_entity" / "_delta_log").is_dir()

    summary = run_seed(settings, mode="dirty")
    assert summary["quality_gate"]["blocked"] is True
    assert summary["gold"]["blocked"] is True
    # Stale gold is removed: it would not represent the dirty dataset.
    assert not (gold / "exec_by_entity").exists()

    # A subsequent clean run rebuilds gold (idempotent recovery).
    run_seed(settings, mode="clean")
    assert (gold / "exec_by_entity" / "_delta_log").is_dir()
