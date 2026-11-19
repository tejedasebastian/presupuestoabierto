from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="presupuesto")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the pipeline")
    run_parser.add_argument(
        "--source",
        required=True,
        choices=["smoke", "seed", "byod"],
    )
    run_parser.add_argument("--mode", default="clean", choices=["clean", "dirty", "volume"])
    run_parser.add_argument("--file", default=None, help="BYOD manifest path (for --source byod)")
    run_parser.add_argument("--volume-entities", type=int, default=None)

    args = parser.parse_args(argv)

    from presupuesto.config import get_settings

    settings = get_settings()

    if args.command == "run":
        if args.source == "smoke":
            from presupuesto.pipeline import run_smoke

            summary = run_smoke(settings)
        elif args.source == "seed":
            from presupuesto.pipeline import run_seed

            summary = run_seed(settings, mode=args.mode)
        elif args.source == "volume":
            from presupuesto.pipeline import run_volume

            summary = run_volume(settings, entities=args.volume_entities)
        elif args.source == "byod":
            from pathlib import Path

            from presupuesto.pipeline import run_byod

            manifest = Path(args.file) if args.file else None
            summary = run_byod(settings, manifest_path=manifest)
        else:
            sys.stderr.write(f"source '{args.source}' is not implemented yet\n")
            return 2
        sys.stdout.write(json.dumps(summary, ensure_ascii=False) + "\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
