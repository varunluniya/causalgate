import os
import tempfile

os.environ["GEN4_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["GEN4_LLM_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

c = TestClient(app)


def test_benchmark_flow():
    assert len(c.get("/questions").json()) == 9
    r = c.post("/benchmarks", json={"model_label": "demo-model-b"}).json()
    assert r["use_cases"]["policy_simulator"]["ship"] is True
    assert c.get(f"/benchmarks/{r['run_id']}").json()["model_label"] == "demo-model-b"
    assert c.post(f"/benchmarks/{r['run_id']}/rerun").status_code == 200
    assert c.post("/overrides", json={"question_id": "F1", "answer": "x", "correct": True}).status_code == 200


def test_errors():
    assert c.post("/benchmarks", json={"model_label": "unknown-model"}).status_code == 404
    assert c.post("/benchmarks", json={"model_label": "m", "backend": "live"}).status_code == 422
    assert c.post("/overrides", json={"question_id": "Q", "answer": "x", "correct": True}).status_code == 404
