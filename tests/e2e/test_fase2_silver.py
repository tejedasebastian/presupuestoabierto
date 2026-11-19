"""E2E for Fase 2: silver grain-aware typing and structural quarantine.

Contract (SPECS 8.2): quarantine holds only structurally unusable rows
(null accrued / unclassifiable concept). Business violations stay in silver
so the quality registry can detect them. Nothing is lost:
bronze == silver + quarantine, exactly.
"""

from __future__ import annotations

from presupuesto.config import get_settings


def _paths():
    settings = get_settings()
    silver = settings.medallion_dir / "silver" / "budget_execution"
    quarantine = settings.medallion_dir / "silver" / "budget_execution_quarantine"
    return settings, silver, quarantine


def test_clean_seed_silver_zero_quarantine(spark_session) -> None:
    from presupuesto.pipeline import run_seed

    settings, silver, quarantine = _paths()
    summary = run_seed(settings, mode="clean")

    assert summary["quarantined_rows"] == 0
    assert summary["silver_rows"] == summary["rows_ingested"]

    silver_df = spark_session.read.format("delta").load(str(silver))
    assert silver_df.count() == summary["rows_ingested"]
    quar_df = spark_session.read.format("delta").load(str(quarantine))
    assert quar_df.count() == 0


def test_silver_types_are_canonical(spark_session) -> None:
    from presupuesto.ingest.seed import YEAR
    from presupuesto.pipeline import run_seed

    settings, silver, _ = _paths()
    run_seed(settings, mode="clean")

    df = spark_session.read.format("delta").load(str(silver))
    types = {field.name: field.dataType.simpleString() for field in df.schema.fields}
    assert types["year"] == "int"
    assert types["month"] == "int"
    assert types["accrued"] == "decimal(18,2)"
    assert types["entity_code"] == "string"

    annual = df.filter(df.grain == "entity_annual").limit(1).collect()[0]
    assert annual["month"] is None
    assert annual["year"] == YEAR
    assert annual["accrued"] is not None

    monthly = df.filter(df.grain == "entity_monthly").limit(1).collect()[0]
    assert monthly["month"] in range(1, 13)


def test_dirty_seed_quarantine_and_conservation(spark_session) -> None:
    """The dirty seed carries one structurally dead row (null accrued).
    It goes to quarantine with a reason; every other violation stays in
    silver; and bronze == silver + quarantine exactly."""
    from presupuesto.pipeline import run_seed

    settings, silver, quarantine = _paths()
    summary = run_seed(settings, mode="dirty")

    assert summary["quarantined_rows"] == 1
    assert summary["silver_rows"] == summary["rows_ingested"] - 1

    quar_df = spark_session.read.format("delta").load(str(quarantine))
    quarantined = quar_df.collect()
    assert len(quarantined) == 1
    assert quarantined[0]["quarantine_reason"] == "null_accrued"
    assert "SIN DEVENGADO" in (quarantined[0]["entity_name"] or "")

    silver_df = spark_session.read.format("delta").load(str(silver))
    assert silver_df.count() + quar_df.count() == summary["rows_ingested"]


def test_dirty_business_violations_stay_in_silver(spark_session) -> None:
    """No silent masking: month 13, the duplicate row, the null pliego and the
    negative PIM must all be IN SILVER for the quality layer to find."""
    from presupuesto.pipeline import run_seed

    settings, silver, _ = _paths()
    run_seed(settings, mode="dirty")

    df = spark_session.read.format("delta").load(str(silver))

    month_13 = df.filter(df.month == 13).count()
    assert month_13 == 1

    null_pliego = df.filter(df.grain == "entity_annual").filter(df.entity_code.isNull()).count()
    assert null_pliego == 1

    sin_dato = df.filter(df.entity_name == "SIN DATO").count()
    assert sin_dato == 1

    negative_pim = df.filter(df.pim < 0).count()
    assert negative_pim == 1

    over_exec = (
        df.filter(df.accrued > df.pim)
        .filter(df.pim > 0)  # negative PIM belongs to validation 10, not 9
        .count()
    )
    assert over_exec == 1
