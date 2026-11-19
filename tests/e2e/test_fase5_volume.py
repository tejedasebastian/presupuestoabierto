"""E2E for Fase 5: volume run through the full medallion + verifiable artifacts.

The suite keeps the volume bounded (1,000 entities = 73,000 rows) so it runs
locally and in CI; the full national-scale run (12,800 entities ~ 934k rows)
runs as a separate CI job with measured timings.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "artifacts" / "e2e"

VOLUME_ENTITIES = 1_000
ROWS_PER_ENTITY = 6 * 12 + 1  # monthly rows per category + annual row
EXPECTED_ROWS = VOLUME_ENTITIES * ROWS_PER_ENTITY


def test_volume_run_full_medallion(spark_session) -> None:
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_volume

    summary = run_volume(get_settings(), entities=VOLUME_ENTITIES)

    assert summary["rows_ingested"] == EXPECTED_ROWS
    assert summary["silver_rows"] == EXPECTED_ROWS
    assert summary["quarantined_rows"] == 0
    assert summary["quality_gate"]["blocked"] is False
    assert summary["quality_summary"]["failed_checks"] == 0
    assert summary["gold"]["blocked"] is False
    assert summary["gold"]["entities"] == VOLUME_ENTITIES
    assert summary["gold"]["monthly_rows"] == VOLUME_ENTITIES * 72

    # Timings are measured, not estimated: every phase reports milliseconds.
    timings = summary["timings_ms"]
    for phase in ("bronze_ms", "silver_ms", "quality_ms", "gold_ms", "total_ms"):
        assert timings[phase] > 0, phase
    assert timings["total_ms"] >= timings["quality_ms"]


def test_artifact_checksums_are_verifiable() -> None:
    """The checksum artifact proves the payload: recompute and compare."""
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    # Self-sufficient: generate the artifacts from a known run.
    run_seed(get_settings(), mode="clean")

    checksums_path = ARTIFACTS / "checksums.sha256"
    report_path = ARTIFACTS / "quality_report.json"
    findings_path = ARTIFACTS / "findings.json"
    by_entity_path = ARTIFACTS / "execution_by_entity.csv"
    category_path = ARTIFACTS / "category_summary.csv"
    department_path = ARTIFACTS / "department_summary.csv"
    summary_path = ARTIFACTS / "gold_summary.csv"
    for path in (
        checksums_path,
        report_path,
        findings_path,
        by_entity_path,
        category_path,
        department_path,
        summary_path,
    ):
        assert path.exists(), path

    recorded = {}
    for line in checksums_path.read_text(encoding="utf-8").strip().splitlines():
        digest, name = line.split("  ", 1)
        recorded[name] = digest

    assert set(recorded) == {
        "quality_report.json",
        "findings.json",
        "execution_by_entity.csv",
        "category_summary.csv",
        "department_summary.csv",
        "gold_summary.csv",
    }
    for name, expected in recorded.items():
        actual = hashlib.sha256((ARTIFACTS / name).read_bytes()).hexdigest()
        assert actual == expected, f"checksum mismatch for {name}"

    manifest_path = ARTIFACTS / "run_manifest.json"
    assert manifest_path.exists()


def test_byod_manifest_declares_provenance() -> None:
    """The committable BYOD manifest must pin grains and entity context."""
    import json

    manifest = json.loads((REPO_ROOT / "data" / "raw" / "byod_manifest.json").read_text("utf-8"))
    grains = {entry["grain"] for entry in manifest["files"]}
    assert grains == {"department", "entity_annual", "entity_monthly", "category_national"}
    monthly = [entry for entry in manifest["files"] if entry["grain"] == "entity_monthly"]
    assert monthly and monthly[0]["context"]["entity_code"] == "301271"
