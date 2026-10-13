"""End-to-end offline cache -> normalized tables -> auditable reports."""

import hashlib
import json
from pathlib import Path

import pytest

from pitwall_historical.__main__ import main
from pitwall_historical.normalize import rebuild


def contents(path):
    return {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}


def test_offline_rebuild_reproduces_all_content_and_provenance(cached_source, tmp_path):
    before = contents(cached_source)
    first, second = tmp_path / "first", tmp_path / "second"
    build = rebuild(cached_source, first)
    rebuild(cached_source, second)
    assert contents(first) == contents(second)
    assert contents(cached_source) == before
    assert build["status"] == "complete"
    assert build["tables"]["laps"]["rows"] == 1
    source_hash = hashlib.sha256((cached_source / "manifest.json").read_bytes()).hexdigest()
    report = json.loads((first / "quality.json").read_text())
    assert report["provenance"]["source_manifest_sha256"] == source_hash
    assert report["provenance"] == build["provenance"]
    assert "PitWall" in (first / "quality.md").read_text()
    with pytest.raises(FileExistsError):
        rebuild(cached_source, first)
    assert contents(first) == contents(second)


def test_cli_offline_success_and_error_exit(cached_source, tmp_path, capsys):
    assert main(["rebuild", str(cached_source), "--output", str(tmp_path / "built")]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["source_import_status"] == "complete"
    assert main(["rebuild", str(cached_source), "--output", str(cached_source)]) == 2
    assert "separate" in capsys.readouterr().err


def test_cache_corruption_cannot_produce_a_report(cached_source, tmp_path):
    manifest = json.loads((cached_source / "manifest.json").read_text())
    raw = cached_source / manifest["requests"][0]["raw_path"]
    raw.write_bytes(b"[]")
    output = tmp_path / "built"
    assert main(["rebuild", str(cached_source), "--output", str(output)]) == 2
    assert not output.exists()


def test_invalid_config_error_is_explicit(tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_text("{}")
    assert main(["import", "--cache", str(tmp_path / "cache"), "--config", str(config)]) == 2
    assert "config" in capsys.readouterr().err


def test_quality_config_is_recorded_and_invalid_threshold_rejected(cached_source, tmp_path):
    config = json.loads(Path("historical/config.json").read_text())
    config["weather_max_age_seconds"] = 60
    build = rebuild(cached_source, tmp_path / "different", config)
    assert build["provenance"]["config"]["weather_max_age_seconds"] == 60
    config["weather_max_age_seconds"] = -1
    with pytest.raises(ValueError, match="weather_max_age_seconds"):
        rebuild(cached_source, tmp_path / "bad", config)
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("override", [None, [], "bad", {"weather_max_age_seconds": 10**400}])
def test_malformed_override_is_explicit_cli_failure(cached_source, tmp_path, capsys, override):
    path = tmp_path / "override.json"
    path.write_text(json.dumps(override))
    output = tmp_path / "built"
    assert (
        main(["rebuild", str(cached_source), "--output", str(output), "--config", str(path)]) == 2
    )
    assert "Historical audit failed:" in capsys.readouterr().err
    assert not output.exists()
