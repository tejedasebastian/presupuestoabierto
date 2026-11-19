"""Pipeline entrypoints. One function per run mode; the CLI only calls these."""

from __future__ import annotations

from presupuesto.config import Settings
from presupuesto.shared.spark import delta_package_version, get_spark


def run_smoke(settings: Settings) -> dict:
    """Fase 0 smoke: boot Spark+Delta, write and read back a tiny Delta table."""
    spark = get_spark(app_name="presupuesto-smoke", driver_memory=settings.driver_memory)
    out_path = settings.medallion_dir / "smoke"

    spark.createDataFrame([(1, "a"), (2, "b"), (3, "c")], ["id", "label"]).write.format(
        "delta"
    ).mode("overwrite").save(str(out_path))

    rows_read_back = spark.read.format("delta").load(str(out_path)).count()

    return {
        "status": "ok",
        "spark_version": spark.version,
        "delta_version": delta_package_version(),
        "rows_written": 3,
        "rows_read_back": rows_read_back,
        "output_path": str(out_path),
        "environment": settings.environment,
    }
