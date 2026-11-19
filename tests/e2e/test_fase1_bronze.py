"""E2E for Fase 1: seed generation, BYOD HTML parsing and bronze Delta write.

The seed generates HTML files in the exact Consulta Amigable export format,
so the real BYOD parser is the only ingestion path: CI never touches the
network and still exercises the production code path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Clean seed expectations: 25 departments + 50 entity-annual rows +
# 2 monthly entities x 12 months + 6 national categories.
CLEAN_EXPECTED_ROWS = 25 + 50 + 24 + 6


def test_cli_seed_clean_run() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "presupuesto", "run", "--source", "seed", "--mode", "clean"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr
    payload = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            payload = json.loads(line)
            break
    assert payload is not None, result.stdout
    assert payload["status"] == "ok"
    assert payload["rows_ingested"] == CLEAN_EXPECTED_ROWS
    assert payload["grain_counts"] == {
        "department": 25,
        "entity_annual": 50,
        "entity_monthly": 24,
        "category_national": 6,
    }
    assert payload["entities"] == 50
    assert payload["files_parsed"] == 5


def test_bronze_delta_written_and_idempotent(spark_session) -> None:
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    settings = get_settings()

    first = run_seed(settings, mode="clean")
    assert first["rows_ingested"] == CLEAN_EXPECTED_ROWS

    bronze_path = settings.medallion_dir / "bronze" / "budget_execution"
    assert (bronze_path / "_delta_log").is_dir()

    df = spark_session.read.format("delta").load(str(bronze_path))
    assert df.count() == CLEAN_EXPECTED_ROWS

    grains = df.groupBy("grain").count().collect()
    grain_counts = {row["grain"]: row["count"] for row in grains}
    assert grain_counts["entity_annual"] == 50
    assert grain_counts["entity_monthly"] == 24

    # Idempotency: re-running the same source replaces, never duplicates.
    second = run_seed(settings, mode="clean")
    assert second["rows_ingested"] == CLEAN_EXPECTED_ROWS
    assert df.count() == CLEAN_EXPECTED_ROWS


def test_seed_dirty_is_fully_ingested(spark_session) -> None:
    """Dirty seed: every parseable row reaches bronze; broken files are
    skipped with explicit file-level failures, never silently."""
    from presupuesto.config import get_settings
    from presupuesto.pipeline import run_seed

    settings = get_settings()
    summary = run_seed(settings, mode="dirty")

    assert summary["rows_ingested"] > CLEAN_EXPECTED_ROWS
    assert summary["file_failures"], "dirty run must report file-level failures"
    failed_names = [f["file"] for f in summary["file_failures"]]
    assert any("schema" in name for name in failed_names)
    assert any("rowcount" in name for name in failed_names)

    bronze_path = settings.medallion_dir / "bronze" / "budget_execution"
    df = spark_session.read.format("delta").load(str(bronze_path))
    assert df.count() == summary["rows_ingested"]


def test_byod_html_fixture_maps_to_canonical_rows(spark_session, tmp_path: Path) -> None:
    """A synthetic export in the real Consulta Amigable format maps to
    canonical bronze rows: UBIGEE-PLIEGO split, month numbers, comma amounts."""
    from presupuesto.ingest.byod import parse_export

    html = """
    <html><body>
    <table id="hd"><tr><td>Fecha de la Consulta: 18-noviembre-2026<br>
    A&ntilde;o de Ejecuci&oacute;n: <span class='value'>2025</span></td></tr></table>
    <table class="MapTable"><tr>
      <td title="Concepto">Municipalidad</td>
      <td title="PIA">PIA</td><td title="PIM">PIM</td>
      <td title="Certificacion">Certificaci&oacute;n</td>
      <td title="Compromiso Anual">Compromiso Anual</td>
      <td title="DEVENGADO">Devengado</td><td title="GIRADO">Girado</td>
    </tr></table>
    <table class="Data">
      <tr><td>150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES</td>
          <td>274,718,541</td><td>387,456,981</td><td>378,061,190</td>
          <td>362,617,233</td><td>362,575,233</td><td>362,575,233</td>
          <td>362,477,865</td><td>93.6</td></tr>
      <tr><td>150101-301250: MUNICIPALIDAD METROPOLITANA DE LIMA</td>
          <td>1,000,000</td><td>2,000,000</td><td>1,900,000</td>
          <td>1,800,000</td><td>1,700,000</td><td>1,700,000</td>
          <td>1,600,000</td><td>85.0</td></tr>
    </table>
    </body></html>
    """
    path = tmp_path / "fixture_entities.xls"
    path.write_text(html, encoding="utf-8")

    rows = parse_export(path, grain="entity_annual")
    assert len(rows) == 2
    row = rows[0]
    assert row["entity_ubigee"] == "150122"
    assert row["entity_code"] == "301271"
    assert row["entity_name"] == "MUNICIPALIDAD DISTRITAL DE MIRAFLORES"
    assert row["year"] == 2025
    assert row["month"] is None
    assert float(row["pia"]) == 274718541.0
    assert float(row["pim"]) == 387456981.0
    assert float(row["accrued"]) == 362575233.0
    assert float(row["execution_pct"]) == 93.6
    assert row["source_file"] == "fixture_entities.xls"


def test_byod_monthly_fixture_with_entity_context(tmp_path: Path) -> None:
    from presupuesto.ingest.byod import parse_export

    html = """
    <html><body>
    <table id="hd"><tr><td>A&ntilde;o de Ejecuci&oacute;n: <span class='value'>2025</span>
    </td></tr></table>
    <table class="MapTable"><tr>
      <td title="Concepto">Mes</td><td title="PIA">PIA</td>
      <td title="PIM">PIM</td><td title="Certificacion">C</td>
      <td title="Compromiso Anual">CA</td><td title="DEVENGADO">Devengado</td>
      <td title="GIRADO">Girado</td>
    </tr></table>
    <table class="Data">
      <tr><td>1: 'Enero</td><td> </td><td> </td><td>55,106,075</td>
          <td>33,345,141</td><td>29,440,692</td><td>14,872,460</td>
          <td>12,486,584</td><td> </td></tr>
      <tr><td>2: 'Febrero</td><td> </td><td> </td><td>94,158,233</td>
          <td>60,000,000</td><td>40,000,000</td><td>20,000,000</td>
          <td>18,000,000</td><td> </td></tr>
    </table>
    </body></html>
    """
    path = tmp_path / "fixture_monthly.xls"
    path.write_text(html, encoding="utf-8")

    rows = parse_export(
        path,
        grain="entity_monthly",
        entity_context={
            "entity_code": "301271",
            "entity_ubigee": "150122",
            "entity_name": "MUNICIPALIDAD DISTRITAL DE MIRAFLORES",
        },
    )
    assert len(rows) == 2
    assert rows[0]["month"] == 1
    assert rows[1]["month"] == 2
    assert rows[0]["entity_code"] == "301271"
    assert rows[0]["pia"] is None  # monthly view leaves PIA/PIM empty
    assert float(rows[0]["accrued"]) == 14872460.0


def test_byod_missing_devengado_column_fails_explicitly(tmp_path: Path) -> None:
    from presupuesto.domain.errors import ValidationError
    from presupuesto.ingest.byod import parse_export

    html = """
    <html><body>
    <table id="hd"><tr><td>A&ntilde;o de Ejecuci&oacute;n: <span class='value'>2025</span>
    </td></tr></table>
    <table class="MapTable"><tr>
      <td title="Concepto">Municipalidad</td>
      <td title="PIA">PIA</td><td title="PIM">PIM</td>
      <td title="Certificacion">C</td>
    </tr></table>
    <table class="Data">
      <tr><td>150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES</td>
          <td>274,718,541</td><td>387,456,981</td><td>378,061,190</td></tr>
    </table>
    </body></html>
    """
    path = tmp_path / "fixture_bad_schema.xls"
    path.write_text(html, encoding="utf-8")

    with pytest.raises(ValidationError) as exc_info:
        parse_export(path, grain="entity_annual")
    assert "DEVENGADO" in exc_info.value.details["missing"]
    assert exc_info.value.details["file"] == "fixture_bad_schema.xls"
