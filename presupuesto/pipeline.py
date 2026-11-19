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


def _ingest_specs(settings: Settings, specs) -> tuple[list[dict], list[dict]]:
    """Parse every export spec; collect rows and explicit file failures.

    File-level failures (schema, minimum rows) skip the file: a truncated or
    schema-broken export is not trustworthy data. Everything else is ingested
    so the quality layer can judge it.
    """
    from presupuesto.domain.errors import ValidationError
    from presupuesto.ingest.byod import parse_export

    rows: list[dict] = []
    failures: list[dict] = []
    for spec in specs:
        try:
            file_rows = parse_export(spec.path, grain=spec.grain, entity_context=spec.context)
            if (
                spec.grain in {"entity_annual", "entity_monthly"}
                and len(file_rows) < settings.min_rows
            ):
                raise ValidationError(
                    "Export is below the minimum row count for its grain.",
                    {"file": spec.path.name, "grain": spec.grain, "rows": len(file_rows)},
                )
            rows.extend(file_rows)
        except ValidationError as exc:
            failures.append(
                {
                    "file": spec.path.name,
                    "grain": spec.grain,
                    "reason": exc.message,
                    "details": exc.details,
                }
            )
    return rows, failures


def run_seed(settings: Settings, mode: str = "clean") -> dict:
    """Generate the seed exports and ingest them through the real BYOD path."""
    from presupuesto.ingest.bronze import write_bronze
    from presupuesto.ingest.seed import generate_seed_files
    from presupuesto.transforms.silver import build_silver, write_silver

    spark = get_spark(app_name="presupuesto-seed", driver_memory=settings.driver_memory)

    specs = generate_seed_files(settings.medallion_dir / "seed", mode)
    rows, file_failures = _ingest_specs(settings, specs)
    out = write_bronze(spark, rows, settings.medallion_dir)

    bronze_df = spark.read.format("delta").load(str(out))
    silver_df, quarantine_df = build_silver(spark, bronze_df)
    silver_path, quarantine_path = write_silver(silver_df, quarantine_df, settings.medallion_dir)

    grain_counts = {
        row["grain"]: row["count"] for row in bronze_df.groupBy("grain").count().collect()
    }
    entities = (
        bronze_df.filter(bronze_df.grain == "entity_annual")
        .select("entity_code")
        .distinct()
        .count()
    )

    return {
        "status": "ok",
        "source": "seed",
        "mode": mode,
        "rows_ingested": len(rows),
        "silver_rows": silver_df.count(),
        "quarantined_rows": quarantine_df.count(),
        "grain_counts": grain_counts,
        "entities": entities,
        "files_parsed": len(specs) - len(file_failures),
        "file_failures": file_failures,
        "bronze_path": str(out),
        "silver_path": str(silver_path),
        "quarantine_path": str(quarantine_path),
    }


def run_volume(settings: Settings, entities: int | None = None) -> dict:
    """Volume stress run: synthetic cross rows written directly to bronze."""
    from presupuesto.ingest.bronze import write_bronze
    from presupuesto.ingest.seed import generate_volume_rows

    spark = get_spark(app_name="presupuesto-volume", driver_memory=settings.driver_memory)
    volume_entities = entities or settings.volume_entities

    rows = generate_volume_rows(volume_entities)
    out = write_bronze(spark, rows, settings.medallion_dir)
    df = spark.read.format("delta").load(str(out))

    return {
        "status": "ok",
        "source": "volume",
        "rows_ingested": len(rows),
        "entities": volume_entities,
        "grain_counts": {
            row["grain"]: row["count"] for row in df.groupBy("grain").count().collect()
        },
        "bronze_path": str(out),
    }
