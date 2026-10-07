import pytest
from fastapi.testclient import TestClient


def test_create_job_empty_recipients(client: TestClient):
    payload = {
        "event_name": "DevFest 2026",
        "issuer_name": "Google",
        "recipients": []
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_create_job_invalid_email_format(client: TestClient):
    payload = {
        "event_name": "DevFest 2026",
        "issuer_name": "Google",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email-address"}
        ]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("Invalid email address format" in str(err) for err in data["detail"])


def test_create_job_empty_recipient_name(client: TestClient):
    payload = {
        "event_name": "DevFest 2026",
        "issuer_name": "Google",
        "recipients": [
            {"name": "   ", "email": "valid@example.com"}
        ]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("Recipient name cannot be empty" in str(err) for err in data["detail"])


def test_create_job_missing_required_fields(client: TestClient):
    payload = {
        "issuer_name": "Google",
        "recipients": [{"name": "Valid User", "email": "valid@example.com"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_whitespace_only_event_name(client: TestClient):
    payload = {
        "event_name": "   ",
        "issuer_name": "Google",
        "recipients": [{"name": "Valid User", "email": "valid@example.com"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
