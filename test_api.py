import json

from fastapi.testclient import TestClient

from crescent_vigil import config as C
from crescent_vigil.api.app import app


def test_health_and_copilot():
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    s = json.loads(open(C.EVAL / "scenarios_dev.jsonl").readline())
    r = c.post("/api/copilot", json={"attendance_id": s["attendance_id"], "now_min": s["now_min"], "question": "what should we watch for"})
    assert r.status_code == 200
    body = r.json()
    assert body["actions"] is not None and "sentences" in body
    assert c.post("/api/copilot", json={"attendance_id": "NOPE", "now_min": 1}).status_code == 404
