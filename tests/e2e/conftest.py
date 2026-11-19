"""Shared E2E fixtures: one Spark session for the whole suite."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def spark_session():
    from presupuesto.config import get_settings
    from presupuesto.shared.spark import get_spark

    spark = get_spark(app_name="presupuesto-e2e", driver_memory=get_settings().driver_memory)
    yield spark
    spark.stop()
