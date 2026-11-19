"""Shared E2E fixtures: one Spark session for the whole suite."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def spark_session():
    from presupuesto.shared.spark import get_spark

    spark = get_spark(app_name="presupuesto-e2e", driver_memory="768m")
    yield spark
    spark.stop()
