"""S1 strict API bounds and preservation of challenge endpoints."""

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app

PAYLOAD = dict(pit_loss_s=18, degradation_multiplier=1, warmup_multiplier=1, grid_size=3)


def test_lab_metadata_comparison_and_challenges_unchanged():
    with TestClient(app) as c:
        before = c.get("/api/v1/challenges").json()
        metadata = c.get("/api/v1/lab")
        assert metadata.status_code == 200 and metadata.json()["grid_max"] == 21
        r = c.post("/api/v1/lab", json=PAYLOAD)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        assert r.json()["comparison"]["strategies"][0]["total_elapsed_s"] == 1113.85
        assert r.json() == c.post("/api/v1/lab", json=PAYLOAD).json()
        assert c.get("/api/v1/challenges").json() == before


@pytest.mark.parametrize(
    "patch",
    [
        {"pit_loss_s": True},
        {"pit_loss_s": "18"},
        {"pit_loss_s": None},
        {"pit_loss_s": 41},
        {"pit_loss_s": -1},
        {"degradation_multiplier": 3.1},
        {"warmup_multiplier": -0.1},
        {"warmup_multiplier": "1"},
        {"grid_size": 22},
        {"grid_size": True},
        {"grid_size": 2.0},
        {"grid_size": 1},
        {"configuration": {}},
        {"schedules": []},
    ],
)
def test_rejected_inputs(patch):
    with TestClient(app) as c:
        r = c.post("/api/v1/lab", json={**PAYLOAD, **patch})
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "body",
    [
        "null",
        "{}",
        "[]",
        '{"pit_loss_s":NaN}',
        '{"pit_loss_s":1e999}',
        '{"pit_loss_s":18,"pit_loss_s":0}',
        "{",
    ],
)
def test_rejected_json(body):
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/v1/lab", content=body, headers={"content-type": "application/json"}
            ).status_code
            == 422
        )


def test_body_content_type_and_query_limits():
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/v1/lab", content=" " * 1025, headers={"content-type": "application/json"}
            ).status_code
            == 413
        )
        assert c.post("/api/v1/lab", content="{}").status_code == 422
        assert c.post("/api/v1/lab?x=1", json=PAYLOAD).status_code == 422
        assert c.get("/api/v1/lab?x=1").status_code == 422
