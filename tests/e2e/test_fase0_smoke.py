"""E2E for Fase 0: Spark + Delta boot and smoke write.

Runs the real pipeline entrypoint (CLI subprocess first, then the shared
session in-process) against a real local Spark with Delta Lake.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = REPO_ROOT / "data" / "medallion" / "smoke"


def test_cli_smoke_run() -> None:
    """The CLI boots Spark with Delta, writes and reads back a Delta table."""
    result = subprocess.run(
        [sys.executable, "-m", "presupuesto", "run", "--source", "smoke"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    # The JVM shutdown hook writes taskkill noise to the same console after
    # our JSON line; parse the JSON line instead of assuming it is last.
    payload = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            payload = json.loads(line)
            break
    assert payload is not None, result.stdout
    assert payload["spark_version"].startswith("4")
    assert payload["delta_version"].startswith("4")
    assert payload["rows_written"] == 3
    assert payload["rows_read_back"] == 3
    assert Path(payload["output_path"]).exists()
    assert (Path(payload["output_path"]) / "_delta_log").is_dir()


@pytest.fixture(scope="module")
def spark_session():
    from presupuesto.shared.spark import get_spark

    spark = get_spark(app_name="presupuesto-e2e-fase0")
    yield spark
    spark.stop()


def test_shared_session_writes_delta(spark_session) -> None:
    """The shared session factory produces exactly one session with Delta."""
    from presupuesto.shared.spark import get_spark

    again = get_spark(app_name="presupuesto-e2e-fase0")
    assert again is spark_session

    out = SMOKE_PATH / "shared_check"
    spark_session.createDataFrame([(1, "a"), (2, "b"), (3, "c")], ["id", "label"]).write.format(
        "delta"
    ).mode("overwrite").save(str(out))
    read_back = spark_session.read.format("delta").load(str(out))
    assert read_back.count() == 3
    assert sorted(row["label"] for row in read_back.collect()) == ["a", "b", "c"]
