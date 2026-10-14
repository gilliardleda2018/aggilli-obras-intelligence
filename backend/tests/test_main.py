from fastapi.testclient import TestClient
from app.main import app, physical_progress, Stage
import pytest

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_demo_progress():
    result = client.get("/api/v1/demo/project")
    assert result.status_code == 200
    assert result.json()["physical_progress"] == 66.0

def test_invalid_weights():
    with pytest.raises(ValueError):
        physical_progress([Stage(name="Fundação", weight=20, progress=100)])
