"""Null-preserving typed normalization and reproducible offline artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path

from . import QUALITY_VERSION, SCHEMA_VERSION
from .schema import SCHEMAS, arrow_schema


def canonical(value: object) -> bytes:
    def default(item):
        if isinstance(item, datetime):
            return item.astimezone(UTC).isoformat()
        raise TypeError(f"Unsupported JSON value: {type(item).__name__}")

    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            default=default,
        )
        + "\n"
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _value(value: object, kind: str, field: str):
    if value is None:
        return None
    if kind == "int":
        valid = type(value) is int and -(2**63) <= value < 2**63
    elif kind == "float":
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
    elif kind == "bool":
        valid = type(value) is bool
    elif kind == "str":
        valid = isinstance(value, str) and bool(value.strip())
    else:
        if not isinstance(value, str):
            raise ValueError(field)
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None or date.utcoffset() is None:
            raise ValueError(field)
        return date.astimezone(UTC)
    if not valid:
        raise ValueError(field)
    if kind in ("int", "float"):
        if (
            field.endswith("_key")
            or field
            in (
                "driver_number",
                "lap_number",
                "lap_start",
                "lap_end",
                "stint_number",
                "position",
            )
        ) and value <= 0:
            raise ValueError(field)
        if (
            field in ("number_of_laps", "tyre_age_at_start", "wind_speed", "pressure")
            or "duration" in field
        ) and value < 0:
            raise ValueError(field)
        if field == "rainfall" and value not in (0, 1):
            raise ValueError(field)
        if field == "humidity" and not 0 <= value <= 100:
            raise ValueError(field)
        if field == "wind_direction" and not 0 <= value < 360:
            raise ValueError(field)
    return float(value) if kind == "float" else value


def normalize_tables(raw_tables: dict[str, list[dict]]) -> dict[str, list[dict]]:
    if set(raw_tables) - set(SCHEMAS):
        raise ValueError("Unknown source table")
    tables = {}
    for table, columns in SCHEMAS.items():
        normalized = []
        for raw in raw_tables.get(table, []):
            errors = []
            row = {}
            original = {k: v for k, v in raw.items() if k not in ("source_request", "source_row")}
            for field, kind in columns.items():
                try:
                    row[field] = _value(raw.get(field), kind, field)
                except (ValueError, OverflowError):
                    row[field] = None
                    errors.append(f"invalid:{field}")
            if table == "pit":
                current, alias = row["lane_duration"], row["pit_duration"]
                if current is not None and alias is not None and current != alias:
                    errors.append("pit_duration_alias_conflict")
                row["effective_lane_duration"] = current if current is not None else alias
                row["lane_duration_source"] = (
                    "lane_duration"
                    if current is not None
                    else "pit_duration"
                    if alias is not None
                    else None
                )
            row.update(
                source_request=raw["source_request"],
                source_row=raw["source_row"],
                raw_json=canonical(original).decode().rstrip("\n"),
                validation_errors=errors,
            )
            normalized.append(row)
        tables[table] = normalized
    return tables


def write_tables(tables: dict[str, list[dict]], output: Path) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    artifacts = {}
    for name, rows in tables.items():
        path = output / f"{name}.parquet"
        table = pa.Table.from_pylist(rows, schema=arrow_schema(name))
        # No inferred types, floating-point rounding, row sorting or deduplication.
        with path.open("xb") as stream:
            pq.write_table(table, stream, compression="zstd", version="2.6")
        artifacts[name] = {
            "path": path.name,
            "rows": len(rows),
            "sha256": digest(path.read_bytes()),
            "logical_sha256": digest(canonical(rows)),
        }
    return artifacts


def _validate_quality_config(config: dict) -> None:
    if type(config.get("max_lap_number")) is not int or config["max_lap_number"] <= 0:
        raise ValueError("config.max_lap_number must be a positive integer")
    for field in (
        "weather_max_age_seconds",
        "timing_tolerance_seconds",
        "sector_tolerance_seconds",
        "min_lap_duration_seconds",
        "max_lap_duration_seconds",
    ):
        value = config.get(field)
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"config.{field} must be finite and positive")
    if config["min_lap_duration_seconds"] >= config["max_lap_duration_seconds"]:
        raise ValueError("lap duration bounds must be increasing")


def rebuild(snapshot: Path, output: Path, config: dict | None = None) -> dict:
    """Rebuild exclusively from verified raw evidence into a never-reused directory."""
    import pyarrow as pa

    from .cache import load_snapshot
    from .quality import build_report, render_markdown

    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    if output == snapshot or snapshot in output.parents or output in snapshot.parents:
        raise ValueError("build output must be separate from the raw snapshot")
    manifest, raw_tables = load_snapshot(snapshot)
    audit_config = manifest["config"] if config is None else config
    if not isinstance(audit_config, dict):
        raise ValueError("audit configuration must be an object")
    audit_config = dict(audit_config)
    _validate_quality_config(audit_config)
    tables = normalize_tables(raw_tables)
    report = build_report(tables, manifest, audit_config)
    report["provenance"] = {
        "source_manifest_sha256": digest((snapshot / "manifest.json").read_bytes()),
        "source_snapshot_id": manifest["snapshot_id"],
        "config": audit_config,
    }
    output.mkdir(parents=True, exist_ok=False)
    build = {
        "schema_version": SCHEMA_VERSION,
        "quality_version": QUALITY_VERSION,
        "status": "building",
        "source_import_status": manifest["status"],
        "provenance": report["provenance"],
        "pyarrow_version": pa.__version__,
        "python_version": platform.python_version(),
        "implementation_sha256": {
            p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
    build_path = output / "build-manifest.json"
    build_path.write_bytes(canonical(build))
    try:
        build["tables"] = write_tables(tables, output)
        reports = {
            "quality.json": canonical(report),
            "quality.md": render_markdown(report).encode("utf-8"),
        }
        for name, data in reports.items():
            (output / name).write_bytes(data)
        build["reports"] = {name: digest(data) for name, data in reports.items()}
        build["status"] = "complete" if manifest["status"] == "complete" else "partial"
    except Exception as exc:
        build["status"] = "failed"
        build["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        build_path.write_bytes(canonical(build))
    return build
