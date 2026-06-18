"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_health_check():
    from app.main import app
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_empty_logs():
    from app.main import app
    client = TestClient(app)
    response = client.post("/analyze", json={"logs": ""})
    assert response.status_code == 400


def test_analyze_missing_field():
    from app.main import app
    client = TestClient(app)
    response = client.post("/analyze", json={"data": "wrong field"})
    assert response.status_code == 422


def test_query_empty_question():
    from app.main import app
    client = TestClient(app)
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 400