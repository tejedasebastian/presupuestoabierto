"""Pipeline entrypoints. One function per run mode; the CLI only calls these.

All modes share one medallion core (_execute_rows): bronze -> silver ->
quality gate -> gold (only if the gate passes) -> artifacts + checksums.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from presupuesto.config import Settings
from presupuesto.shared.spark import delta_package_version, get_spark


def _artifacts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "artifacts" / "e2e"


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
                    {
                        "file": spec.path.name,
                        "grain": spec.grain,
                        "rows": len(file_rows),
                        "check": "raw_row_count",
                    },
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


def _execute_rows(
    settings: Settings,
    rows: list[dict],
    file_failures: list[dict],
    files_attempted: int,
    source: str,
    mode: str,
    source_hashes: dict[str, str] | None = None,
) -> dict:
    """Shared medallion core. Gold only exists when the gate passes."""
    from presupuesto.analytics.gold import remove_gold, write_findings, write_gold
    from presupuesto.ingest.bronze import write_bronze
    from presupuesto.quality.registry import run_quality, write_quality_report
    from presupuesto.reporting.artifacts import write_run_artifacts
    from presupuesto.reporting.exports import write_exec_by_entity_csv, write_gold_summary_csv
    from presupuesto.transforms.silver import build_silver, write_silver

    artifacts = _artifacts_dir()
    timings: dict[str, float] = {}
    total_started = time.perf_counter()
    spark = get_spark(app_name=f"presupuesto-{source}", driver_memory=settings.driver_memory)

    started = time.perf_counter()
    bronze_path = write_bronze(spark, rows, settings.medallion_dir)
    bronze_df = spark.read.format("delta").load(str(bronze_path))
    timings["bronze_ms"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    silver_df, quarantine_df = build_silver(spark, bronze_df)
    silver_path, quarantine_path = write_silver(silver_df, quarantine_df, settings.medallion_dir)
    timings["silver_ms"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    quality = run_quality(
        silver_df,
        file_failures=file_failures,
        files_attempted=files_attempted,
        settings=settings,
    )
    report_path = write_quality_report(quality, artifacts)
    timings["quality_ms"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    if quality["gate"]["blocked"]:
        remove_gold(settings.medallion_dir)
        gold_summary = {"blocked": True, "entities": 0, "monthly_rows": 0}
    else:
        gold_result = write_gold(
            spark,
            silver_df,
            settings.medallion_dir,
            low_threshold=settings.low_execution_threshold,
        )
        write_findings(gold_result["findings"], artifacts)
        write_exec_by_entity_csv(gold_result["exec_by_entity"], artifacts)
        write_gold_summary_csv(gold_result["exec_by_entity"], gold_result["findings"], artifacts)
        gold_summary = {
            "blocked": False,
            "entities": gold_result["entities"],
            "monthly_rows": gold_result["monthly_rows"],
        }
    timings["gold_ms"] = round((time.perf_counter() - started) * 1000, 2)

    grain_counts = {
        row["grain"]: row["count"] for row in bronze_df.groupBy("grain").count().collect()
    }
    entities = (
        bronze_df.filter(bronze_df.grain == "entity_annual")
        .select("entity_code")
        .distinct()
        .count()
    )

    summary = {
        "status": "ok",
        "source": source,
        "mode": mode,
        "rows_ingested": len(rows),
        "silver_rows": silver_df.count(),
        "quarantined_rows": quarantine_df.count(),
        "quality_summary": quality["summary"],
        "quality_gate": quality["gate"],
        "quality_report": str(report_path),
        "gold": gold_summary,
        "grain_counts": grain_counts,
        "entities": entities,
        "files_parsed": files_attempted - len(file_failures),
        "file_failures": file_failures,
        "bronze_path": str(bronze_path),
        "silver_path": str(silver_path),
        "quarantine_path": str(quarantine_path),
        "timings_ms": timings,
    }

    started = time.perf_counter()
    timings["total_ms"] = round((time.perf_counter() - total_started) * 1000, 2)
    manifest_path = write_run_artifacts(
        artifacts,
        summary,
        source_hashes=source_hashes or {},
        spark_version=spark.version,
        delta_version=delta_package_version(),
    )
    summary["run_manifest"] = str(manifest_path)
    return summary


def run_seed(settings: Settings, mode: str = "clean") -> dict:
    """Generate the seed exports and ingest them through the real BYOD path."""
    from presupuesto.ingest.seed import generate_seed_files

    specs = generate_seed_files(settings.medallion_dir / "seed", mode)
    rows, file_failures = _ingest_specs(settings, specs)
    return _execute_rows(
        settings,
        rows,
        file_failures,
        files_attempted=len(specs),
        source="seed",
        mode=mode,
    )


def run_byod(settings: Settings, manifest_path: Path | None = None) -> dict:
    """Run the pipeline over the real BYOD exports declared in the manifest."""
    from presupuesto.ingest.seed import FileSpec
    from presupuesto.reporting.artifacts import sha256_file

    manifest_file = manifest_path or (settings.raw_dir / "byod_manifest.json")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    specs = []
    source_hashes: dict[str, str] = {}
    for entry in manifest["files"]:
        path = settings.raw_dir / entry["path"]
        specs.append(
            FileSpec(
                path=path,
                grain=entry["grain"],
                context=entry.get("context", {}),
            )
        )
        source_hashes[entry["path"]] = sha256_file(path)

    rows, file_failures = _ingest_specs(settings, specs)
    return _execute_rows(
        settings,
        rows,
        file_failures,
        files_attempted=len(specs),
        source="byod",
        mode=manifest.get("label", "real"),
        source_hashes=source_hashes,
    )


def run_volume(settings: Settings, entities: int | None = None) -> dict:
    """Volume stress run: synthetic cross rows, full medallion with timings."""
    from presupuesto.ingest.seed import generate_volume_rows

    volume_entities = entities or settings.volume_entities
    rows = generate_volume_rows(volume_entities)
    summary = _execute_rows(
        settings,
        rows,
        file_failures=[],
        files_attempted=0,
        source="volume",
        mode=f"{volume_entities}_entities",
    )
    summary["volume_entities"] = volume_entities
    return summary
