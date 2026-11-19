"""Run artifacts: manifest of the run and SHA-256 checksums.

The manifest records provenance (including per-file hashes for BYOD), counts,
quality/gold summaries and phase timings. checksums.sha256 covers the payload
artifacts; manifest and checksums themselves are excluded (circular).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

PAYLOAD_ARTIFACTS = (
    "quality_report.json",
    "findings.json",
    "execution_by_entity.csv",
    "gold_summary.csv",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_run_artifacts(
    artifacts_dir: Path,
    summary: dict,
    source_hashes: dict[str, str],
    spark_version: str,
    delta_version: str,
) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_hashes = {
        name: sha256_file(artifacts_dir / name)
        for name in PAYLOAD_ARTIFACTS
        if (artifacts_dir / name).exists()
    }

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": summary["source"],
        "mode": summary["mode"],
        "spark_version": spark_version,
        "delta_version": delta_version,
        "rows_ingested": summary["rows_ingested"],
        "silver_rows": summary["silver_rows"],
        "quarantined_rows": summary["quarantined_rows"],
        "entities": summary["entities"],
        "quality_summary": summary["quality_summary"],
        "quality_gate": summary["quality_gate"],
        "gold": summary["gold"],
        "timings_ms": summary["timings_ms"],
        "source_files_sha256": source_hashes,
        "artifacts_sha256": artifact_hashes,
        "checksums_note": (
            "checksums.sha256 covers the four payload artifacts; it cannot "
            "cover run_manifest.json or itself without a circular dependency."
        ),
    }
    manifest_path = artifacts_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    checksum_lines = "\n".join(
        f"{digest}  {name}" for name, digest in sorted(artifact_hashes.items())
    )
    (artifacts_dir / "checksums.sha256").write_text(checksum_lines + "\n", encoding="utf-8")
    return manifest_path
