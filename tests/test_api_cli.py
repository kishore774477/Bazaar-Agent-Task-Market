import pytest
from fastapi.testclient import TestClient

from bazaar import server
from bazaar.cli import main


@pytest.fixture()
def client():
    app = server.create_app(precompute=False)
    with TestClient(app) as c:
        yield c


def test_meta_and_summary(client):
    m = client.get("/api/meta").json()
    assert m["seed"] == 1 and m["n_tasks"] == 240 and len(m["roster"]) == 10 and len(m["categories"]) == 8
    assert m["sweep_ready"] is False
    s = client.get("/api/summary").json()
    assert s["bazaar"]["n_tasks"] == 240 and len(s["hires"]) == 8
    rep = client.get("/api/reputation").json()
    assert set(rep) == {r["name"] for r in m["roster"]}


def test_auctions_filter_and_pagination(client):
    a = client.get("/api/auctions", params={"system": "bazaar"}).json()
    assert a["total"] == 240 and len(a["items"]) == 240
    d = client.get("/api/auctions", params={"system": "bazaar", "category": "data"}).json()
    assert d["total"] < a["total"] and all(it["task"]["category"] == "data" for it in d["items"])
    page = client.get("/api/auctions", params={"system": "crew", "limit": 5, "offset": 10}).json()
    assert len(page["items"]) == 5
    assert client.get("/api/auctions", params={"system": "nope"}).status_code == 400


def test_run_validates_and_updates_state(client):
    r = client.post("/api/run", json={"seed": 5, "n_tasks": 40}).json()
    assert r == {"seed": 5, "n_tasks": 40}
    assert client.get("/api/meta").json()["seed"] == 5
    assert client.get("/api/summary").json()["n_tasks"] == 40
    assert client.post("/api/run", json={"n_tasks": 5}).status_code == 400
    assert client.post("/api/run", json={"n_tasks": 99999}).status_code == 400
    assert client.post("/api/run", json={"weights": [0.5, 0.5, 0.5]}).status_code == 400
    assert client.post("/api/run", json={"weights": [0.5, 0.5]}).status_code == 400
    ok = client.post("/api/run", json={"weights": [0.2, 0.3, 0.5]})
    assert ok.status_code == 200 and client.get("/api/meta").json()["weights"] == [0.2, 0.3, 0.5]


def test_sweep_endpoint(client):
    assert client.get("/api/sweep").json() == {"result": None, "computing": False}
    r = client.post("/api/sweep", params={"n_seeds": 5, "n_tasks": 60})
    assert r.status_code == 200 and r.json()["n_seeds"] == 5
    assert client.get("/api/sweep").json()["result"]["n_seeds"] == 5
    assert client.post("/api/sweep", params={"n_seeds": 1}).status_code == 400
    assert client.post("/api/sweep", params={"n_tasks": 5}).status_code == 400


def test_dashboard_is_served(client):
    assert "Bazaar" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/style.css").status_code == 200


# ---------------------------------------------------------------------------- CLI
def test_cli_run(capsys):
    main(["--tasks", "80", "run", "--seed", "1"])
    out = capsys.readouterr().out
    assert "80 tasks, seed 1" in out and "bazaar" in out and "crew" in out
    assert "the crew hired" in out


def test_cli_sweep(capsys):
    main(["--tasks", "60", "sweep", "--seeds", "5"])
    out = capsys.readouterr().out
    assert "5 seeds x 60 tasks" in out
    assert "bazaar beats crew in" in out
    assert "Flex" in out
