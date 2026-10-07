from fastapi.testclient import TestClient


def test_retrieve_and_download_certificate(client: TestClient):
    payload = {
        "event_name": "API Design Masterclass",
        "issuer_name": "Tech Corp",
        "recipients": [
            {"name": "Leonardo Da Vinci", "email": "leo@renaissance.org"}
        ]
    }
    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    cert = status_resp.json()["certificates"][0]
    cert_id = cert["id"]
    cert_code = cert["certificate_code"]

    # 1. Retrieve single certificate metadata
    cert_resp = client.get(f"/api/v1/certificates/{cert_id}")
    assert cert_resp.status_code == 200
    assert cert_resp.json()["recipient_name"] == "Leonardo Da Vinci"
    assert cert_resp.json()["status"] == "SUCCESS"

    # 2. Download certificate PDF
    dl_resp = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert dl_resp.content.startswith(b"%PDF-")

    # 3. Verify certificate by unique verification code
    verify_resp = client.get(f"/api/v1/certificates/verify/{cert_code}")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["valid"] is True
    assert v_data["certificate_code"] == cert_code
    assert v_data["recipient_name"] == "Leonardo Da Vinci"
    assert v_data["event_name"] == "API Design Masterclass"
    assert v_data["issuer_name"] == "Tech Corp"
    assert v_data["checksum_hash"] == cert["checksum_hash"]


def test_verify_invalid_certificate_code(client: TestClient):
    verify_resp = client.get("/api/v1/certificates/verify/CERT-DOES-NOT-EXIST")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["valid"] is False
    assert "not found" in v_data["message"].lower()


def test_download_non_existent_certificate(client: TestClient):
    response = client.get("/api/v1/certificates/00000000-0000-0000-0000-000000000000/download")
    assert response.status_code == 404


def test_download_zip_archive(client: TestClient):
    payload = {
        "event_name": "Distributed Systems Summit",
        "issuer_name": "Cloud Native Org",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@cloud.org"},
            {"name": "Bob Jones", "email": "bob@cloud.org"}
        ]
    }
    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    # Download ZIP
    zip_resp = client.get(f"/api/v1/jobs/{job_id}/download-zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    assert "attachment;" in zip_resp.headers["content-disposition"]


def test_download_zip_non_existent_job(client: TestClient):
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/download-zip")
    assert response.status_code == 404


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "storage" in data

