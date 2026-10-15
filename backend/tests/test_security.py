from fastapi.testclient import TestClient
from app.main import app
from app.projects import router

client = TestClient(app)
def test_unconfigured_auth_fails_closed():
    response = client.get("/api/v1/projects")
    assert response.status_code == 503
