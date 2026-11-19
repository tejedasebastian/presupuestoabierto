"""E2E for Fase 3: the twelve quality validations with gate.

The medium-hard scenario of the whole project: the dirty seed injects exactly
one violation per validation, and the E2E demands the report detects all
twelve with exact counts, and that the gate blocks gold.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "artifacts" / "e2e"

ALL_CHECKS = [
    "raw_schema_present",
    "raw_row_count",
    "raw_parseable",
    "silver_types",
    "silver_no_null_keys",
    "silver_unique_keys",
    "silver_catalog_referential",
    "silver_entity_named",
    "business_devengado_le_pim",
    "business_amounts_positive",
    "business_monthly_sums_to_annual",
    "business_coverage_months",
]


def _read_report() -> dict:
    report_path = ARTIFACTS / "quality_report.json"
    assert report_path.exists(), report_path
    return json.loads(report_path.read_text(encoding="utf-8"))


def test_clean_seed_twelve_pass(spark_session) -> None:
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    run_seed(get_settings(), mode="clean")
    report = _read_report()

    checks = {check["name"]: check for check in report["checks"]}
    assert sorted(checks) == sorted(ALL_CHECKS)
    for name, check in checks.items():
        assert check["status"] == "pass", f"{name}: {check}"
    assert report["summary"]["failed_checks"] == 0
    assert report["summary"]["warn_checks"] == 0
    assert report["gate"]["blocked"] is False


def test_dirty_seed_detects_all_twelve(spark_session) -> None:
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    run_seed(get_settings(), mode="dirty")
    report = _read_report()

    checks = {check["name"]: check for check in report["checks"]}
    assert sorted(checks) == sorted(ALL_CHECKS)

    # One violation per validation, with the exact expected counts.
    expected_failed = {
        "raw_schema_present": 1,  # file without DEVENGADO
        "raw_row_count": 1,  # file below min_rows
        "raw_parseable": 1,  # PIM "12,3x4"
        "silver_types": 1,  # month 13
        "silver_no_null_keys": 1,  # missing pliego
        "silver_unique_keys": 1,  # duplicated row (extra rows)
        "silver_catalog_referential": 12,  # unknown pliego 301999, 12 monthly rows
        "silver_entity_named": 1,  # "SIN DATO"
        "business_devengado_le_pim": 1,  # accrued 300 > pim 200
        "business_amounts_positive": 1,  # PIM -5,000
        "business_monthly_sums_to_annual": 1,  # entity 301001
        "business_coverage_months": 1,  # entity 301002 with 6 months
    }
    for name, expected in expected_failed.items():
        assert checks[name]["rows_failed"] == expected, (
            f"{name}: expected {expected}, got {checks[name]['rows_failed']}"
        )

    # The dirty run must block gold.
    assert report["gate"]["blocked"] is True
    blocking = report["gate"]["blocking_checks"]
    assert "raw_schema_present" in blocking
    assert "silver_types" in blocking
    assert "business_devengado_le_pim" in blocking


def test_quality_report_has_evidence_fields(spark_session) -> None:
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    run_seed(get_settings(), mode="dirty")
    report = _read_report()

    for check in report["checks"]:
        assert check["layer"] in {"file", "bronze", "silver"}
        assert check["level"] in {"fail", "warn"}
        assert check["status"] in {"pass", "warn", "fail"}
        assert check["rows_checked"] >= check["rows_failed"]
        assert "duration_ms" in check
        assert isinstance(check["failed_sample"], list)
        assert len(check["failed_sample"]) <= 20
        # The report must cite the SQL/condition it ran.
        assert check["sql"].strip()

    failed_with_samples = [
        check for check in report["checks"] if check["rows_failed"] > 0 and check["layer"] != "file"
    ]
    assert failed_with_samples, "dirty run must produce row-level failures"
    for check in failed_with_samples:
        assert check["failed_sample"], f"{check['name']} must carry a failed row sample"
