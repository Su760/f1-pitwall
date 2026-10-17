"""Known-answer description and frozen-evidence failures; artificial data only."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree

import pytest

from historical.tests.test_cohort import SELECTION, verified_session_manifest
from historical.tests.test_quality import CONFIG, START, fixture, row
from pitwall_historical import descriptive
from pitwall_historical.cohort import audit_snapshot
from pitwall_historical.normalize import canonical, digest


def samples(values):
    return [
        {"source_request": "laps", "source_row": i, "lap_number": i + 1, "lap_duration_seconds": v}
        for i, v in enumerate(values)
    ]


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], (None, None, None, None)),
        ([90], (90, 90, 90, 0)),
        ([90, 94], (91, 92, 93, 2)),
        ([1, 2, 3, 4], (1.75, 2.5, 3.25, 1.5)),
        ([1, 2, 10, 12, 20], (2, 10, 12, 10)),
    ],
)
def test_known_quantiles(values, expected):
    result = descriptive.summarize(samples(values))
    assert (
        tuple(result[f] for f in ("q1_seconds", "median_seconds", "q3_seconds", "iqr_seconds"))
        == expected
    )
    assert result["n"] == len(values)
    assert result["source_rows"] == [descriptive.ref(r) for r in samples(values)]


@pytest.mark.parametrize("value", [None, 0, float("nan"), float("inf"), True])
def test_invalid_duration_never_becomes_zero(value):
    with pytest.raises(ValueError, match="duration"):
        descriptive.summarize(samples([value]))


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    """Mock only cache transport boundary; actual F1.2/quality code and hashes run."""
    tables = fixture()
    tables["race_control"].append(
        row(
            "race_control",
            index=1,
            date=START,
            category="Other",
            message="CAR 1 (FIX) TIME 1:30.000 DELETED - TRACK LIMITS LAP 3",
        )
    )
    raw = json.loads(canonical(tables))
    manifest = {**verified_session_manifest(), "config": CONFIG}
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "manifest.json").write_bytes(canonical(manifest))
    import pitwall_historical.cache as cache

    monkeypatch.setattr(cache, "load_snapshot", lambda _: (manifest, raw))
    monkeypatch.setattr(descriptive, "load_snapshot", lambda _: (manifest, raw))
    import pitwall_historical.cohort as cohort_module

    monkeypatch.setattr(cohort_module, "load_snapshot", lambda _: (manifest, raw))
    selection = tmp_path / "selection.json"
    selection.write_bytes(canonical(SELECTION))
    cohort = tmp_path / "cohort"
    audit_snapshot(snapshot, cohort, selection)
    pin = tmp_path / "pin.json"
    pin.write_bytes(
        canonical(
            {
                "version": descriptive.VERSION,
                "cohort_manifest_sha256": digest((cohort / "manifest.json").read_bytes()),
            }
        )
    )
    return snapshot, cohort, pin


def test_frozen_build_reconciliation_sensitivity_and_determinism(frozen, tmp_path):
    before = {str(p): p.read_bytes() for root in frozen[:2] for p in root.rglob("*") if p.is_file()}
    a, b = tmp_path / "a", tmp_path / "b"
    stats = descriptive.generate(*frozen, a)
    descriptive.generate(*frozen, b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {
        p.name: p.read_bytes() for p in b.iterdir()
    }
    assert stats["reconciliation"] == {
        "source_laps": 4,
        "primary": 3,
        "excluded": 1,
        "deletion_tagged": 1,
        "sensitivity": 2,
    }
    g = stats["driver_stints"][0]
    assert g["primary"]["race_laps"] == [2, 3, 4]
    assert g["sensitivity"]["race_laps"] == [2, 4]
    assert g["omitted_tagged_rows"] == [{"source_request": "laps-fixture", "source_row": 2}]
    assert stats["full_circuit_gate"]["status"] == "blocked"
    assert stats["source_snapshot_status"] == "partial"
    assert before == {
        str(p): p.read_bytes() for root in frozen[:2] for p in root.rglob("*") if p.is_file()
    }
    assert (
        descriptive.main(
            [
                str(frozen[0]),
                "--cohort",
                str(frozen[1]),
                "--config",
                str(frozen[2]),
                "--output",
                str(tmp_path / "cli"),
            ]
        )
        == 2
    )
    with pytest.raises(FileExistsError):
        descriptive.generate(*frozen, a)


@pytest.mark.parametrize(
    "name", ["manifest.json", "membership.json", "exclusions.json", "audit.json"]
)
def test_corrupt_frozen_artifact_fails_before_writing(frozen, tmp_path, name):
    path = frozen[1] / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        descriptive.generate(*frozen, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_provenance_code_drift_and_raw_manifest_fails(frozen, tmp_path, monkeypatch):
    original = Path.read_bytes

    def changed_code(path):
        data = original(path)
        return data + b"\n" if path.name == "quality.py" else data

    monkeypatch.setattr(Path, "read_bytes", changed_code)
    with pytest.raises(ValueError, match="code drift"):
        descriptive.generate(*frozen, tmp_path / "drift")
    monkeypatch.setattr(Path, "read_bytes", original)
    path = frozen[0] / "manifest.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source manifest"):
        descriptive.generate(*frozen, tmp_path / "raw")
    assert not (tmp_path / "raw").exists()


def test_reconciliation_identity_and_empty_sensitivity(frozen):
    tables, members, excluded, audit, provenance = descriptive.verified_inputs(*frozen)
    original = deepcopy(members)
    for member in members:
        audit["deletions"]["messages"][0]["included_source_rows"].append(descriptive.ref(member))
    audit["deletions"]["included_rows_with_explicit_deletion"] = len(members)
    stats = descriptive.statistics(tables, members, excluded, audit, provenance)
    assert stats["driver_stints"][0]["sensitivity"]["n"] == 0
    assert stats["driver_stints"][0]["sensitivity"]["median_seconds"] is None
    assert members == original
    with pytest.raises(ValueError, match="partition"):
        descriptive.statistics(tables, members, excluded + members[:1], audit, provenance)
    tables["laps"][members[0]["source_row"]]["driver_number"] = 99
    with pytest.raises(ValueError, match="identity join"):
        descriptive.statistics(tables, members, excluded, audit, provenance)


def test_svg_gaps_annotations_and_html_escaping(frozen):
    tables, members, excluded, audit, provenance = descriptive.verified_inputs(*frozen)
    tables["drivers"][0]["full_name"] = "<script>alert(1)</script>"
    stats = descriptive.statistics(tables, members, excluded, audit, provenance)
    html, _ = descriptive.render(stats)
    assert b"<script>alert(1)</script>" not in html
    assert b"&lt;script&gt;" in html
    assert b"not simultaneous clock time" in html
    assert b"not a certified-clean subset" in html
    rows = [stats["rows"][0], stats["rows"][2]]
    svg = descriptive.chart(stats["driver_stints"][0], rows, [2, 4], [89, 91])
    root = ElementTree.fromstring(svg)
    assert not root.findall(".//{*}polyline")
    assert len(root.findall(".//{*}circle")) == 2
    svg = descriptive.chart(stats["driver_stints"][0], stats["rows"], [2, 4], [89, 91])
    root = ElementTree.fromstring(svg)
    assert root.find(".//{*}polyline").get("data-laps") == "2,3,4"
    assert len([e for e in root.findall(".//{*}path") if e.get("data-tagged-lap")]) == 1


def test_real_cache_corruption_is_rejected(cached_source, tmp_path):
    # Use actual cache validator here; earlier synthetic fixture mocks that boundary only.
    manifest = json.loads((cached_source / "manifest.json").read_text())
    (cached_source / manifest["requests"][0]["raw_path"]).write_bytes(b"[]")
    with pytest.raises(ValueError):
        descriptive.load_snapshot(cached_source)
