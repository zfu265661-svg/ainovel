from fastapi.testclient import TestClient

from interfaces.api.main import app


def test_fastapi_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_project_chapter_trace_audit_report_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_ENGINE_PROJECTS_ROOT", str(tmp_path))
    client = TestClient(app)

    created = client.post("/projects", json={"name": "Demo", "project_id": "demo"})
    assert created.status_code == 200
    assert created.json()["project"]["project_id"] == "demo"

    run = client.post("/projects/demo/chapters/1/run", json={})
    assert run.status_code == 200
    assert run.json()["status"] == "success"

    assert client.get("/projects").status_code == 200
    assert client.get("/projects/demo").json()["project"]["project_id"] == "demo"
    assert client.get("/projects/demo/snapshot").json()["current_chapter"] == 1
    assert client.get("/projects/demo/chapters").json()[0]["has_trace"] is True
    assert client.get("/projects/demo/chapters/1/trace").json()["status"] == "success"
    assert client.get("/projects/demo/chapters/1/context-audit").json()["budget"]["selected_items"] > 0
    assert "findings" in client.get("/projects/demo/chapters/1/consistency-report").json()
    assert client.get("/projects/demo/plot-threads").json()[0]["id"] == "main-thread"
    assert client.get("/projects/demo/foreshadows").json()[0]["id"] == "opening-hook"
    assert client.get("/projects/demo/checkpoints").json()[0]["checkpoint_id"] == "checkpoint_ch001"
