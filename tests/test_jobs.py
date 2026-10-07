from fastapi.testclient import TestClient


def test_create_and_process_job_successfully(client: TestClient):
    payload = {
        "event_name": "Fullstack Cloud Workshop",
        "issuer_name": "DevOps Council",
        "issue_date": "October 07, 2026",
        "recipients": [
            {"name": "Sarah Connor", "email": "sarah@resistance.org"},
            {"name": "John Connor", "email": "john@resistance.org"}
        ]
    }

    # 1. Submit job (returns 202 Accepted)
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total_recipients"] == 2
    job_id = data["job_id"]

    # 2. Query status (TestClient processes background task synchronously)
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    job_data = status_resp.json()

    assert job_data["id"] == job_id
    assert job_data["status"] == "COMPLETED"
    assert job_data["total_count"] == 2
    assert job_data["processed_count"] == 2
    assert job_data["success_count"] == 2
    assert job_data["failure_count"] == 0
    assert job_data["progress_percentage"] == 100.0
    assert len(job_data["certificates"]) == 2

    # Check certificate data
    for cert in job_data["certificates"]:
        assert cert["status"] == "SUCCESS"
        assert cert["error_message"] is None
        assert cert["download_url"] is not None
        assert cert["verify_url"] is not None


def test_list_jobs_pagination(client: TestClient):
    # Create two jobs
    for i in range(2):
        client.post("/api/v1/jobs", json={
            "event_name": f"Event {i}",
            "issuer_name": "Issuer Org",
            "recipients": [{"name": f"User {i}", "email": f"user{i}@example.com"}]
        })

    response = client.get("/api/v1/jobs?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert data["total_jobs"] >= 2
    assert len(data["jobs"]) >= 2


def test_get_non_existent_job(client: TestClient):
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
