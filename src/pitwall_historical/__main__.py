"""Explicit online import and offline rebuild commands for the F1 audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenF1 retrospective suitability audit (F1)")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("import", help="fetch a new immutable bounded raw snapshot")
    ingest.add_argument("--cache", type=Path, required=True)
    ingest.add_argument("--config", type=Path, required=True)
    offline = commands.add_parser(
        "rebuild", help="verify cache and rebuild Parquet + quality offline"
    )
    offline.add_argument("snapshot", type=Path)
    offline.add_argument("--output", type=Path, required=True)
    offline.add_argument("--config", type=Path, help="explicit audit thresholds override")
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            from .cache import import_snapshot

            config = _config(args.config)
            path = import_snapshot(args.cache, config)
            manifest = json.loads((path / "manifest.json").read_text())
            print(json.dumps({"snapshot": str(path), "status": manifest["status"]}))
            return 0 if manifest["status"] == "complete" else 2
        from .normalize import rebuild

        config = _config(args.config) if args.config else None
        build = rebuild(args.snapshot, args.output, config)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "status": build["status"],
                    "source_import_status": build["source_import_status"],
                }
            )
        )
        return 0 if build["status"] == "complete" else 2
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"Historical audit failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
