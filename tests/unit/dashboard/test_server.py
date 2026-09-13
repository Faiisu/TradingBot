import pytest
from fastapi.testclient import TestClient

from tradebot.dashboard import server

LOCAL = "http://127.0.0.1:8765"
JSON = {"Content-Type": "application/json"}


class _FakeSupervisor:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def status(self):
        return {"state": "stopped", "pid": None, "started_at": None, "stop_requested_at": None, "exit_code": None, "log_tail": []}

    def start(self):
        self.started += 1
        return {**self.status(), "state": "running"}

    def stop(self):
        self.stopped += 1
        return {**self.status(), "state": "stopping"}


@pytest.fixture
def fake_supervisor(monkeypatch):
    fake = _FakeSupervisor()
    monkeypatch.setattr(server, "supervisor", fake)
    monkeypatch.setattr(server, "ensemble_summary", lambda: {"members": 25, "saved_at": None})
    return fake


@pytest.fixture
def client():
    return TestClient(server.app, base_url=LOCAL)


def test_start_from_the_dashboard_page_is_allowed(client, fake_supervisor):
    response = client.post("/api/paper/start", headers={**JSON, "Origin": LOCAL}, content="{}")
    assert response.status_code == 200
    assert fake_supervisor.started == 1


def test_start_from_another_site_is_rejected(client, fake_supervisor):
    response = client.post("/api/paper/start", headers={**JSON, "Origin": "https://evil.example"}, content="{}")
    assert response.status_code == 403
    assert fake_supervisor.started == 0


def test_start_without_a_json_content_type_is_rejected(client, fake_supervisor):
    # a plain HTML form post needs no CORS preflight, so it must not be accepted
    response = client.post(
        "/api/paper/start", headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": LOCAL}, content="a=1"
    )
    assert response.status_code == 415
    assert fake_supervisor.started == 0


def test_dns_rebinding_host_is_rejected(fake_supervisor):
    rebound = TestClient(server.app, base_url="http://evil.example:8765")
    response = rebound.post("/api/paper/stop", headers={**JSON, "Origin": "http://evil.example:8765"}, content="{}")
    assert response.status_code == 403
    assert fake_supervisor.stopped == 0


def test_start_is_refused_when_there_is_no_ensemble(client, fake_supervisor, monkeypatch):
    monkeypatch.setattr(server, "ensemble_summary", lambda: {"members": 0, "saved_at": None})
    response = client.post("/api/paper/start", headers={**JSON, "Origin": LOCAL}, content="{}")
    assert response.status_code == 409
    assert fake_supervisor.started == 0


def test_status_includes_the_ensemble_that_start_would_trade(client, fake_supervisor):
    body = client.get("/api/paper/status").json()
    assert body["state"] == "stopped"
    assert body["ensemble"]["members"] == 25
