"""
Integration tests for PC4 Feedback Service
"""
import pytest
import json
from feedback import app, SpeakRequest
from fastapi.testclient import TestClient

client = TestClient(app)


def test_feedback_service_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "feedback-service"


def test_feedback_service_speak():
    """Test speak endpoint"""
    response = client.post(
        "/speak",
        json={"message": "Test message", "priority": "normal"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Test message"
    assert data["spoken"] in [True, False]


def test_feedback_service_speak_priorities():
    """Test speak with different priorities"""
    priorities = ["low", "normal", "high", "emergency"]
    for priority in priorities:
        response = client.post(
            "/speak",
            json={"message": "Test", "priority": priority}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == priority


def test_feedback_service_announce():
    """Test announce endpoint"""
    response = client.post(
        "/announce",
        json={"event": "takeoff", "details": "Ready for flight"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "announced"
    assert data["event"] == "takeoff"


def test_feedback_service_voices():
    """Test voices endpoint"""
    response = client.get("/voices")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert isinstance(data["voices"], list)


def test_feedback_service_stats():
    """Test stats endpoint"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "queue_stats" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
