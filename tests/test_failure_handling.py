import io
import zipfile
from fastapi.testclient import TestClient


def test_individual_failure_isolation(client: TestClient):
    """
    Core Requirement Test:
    A failure while generating one certificate should NOT prevent other
    valid certificates in the same job from being generated.
    """
    payload = {
        "event_name": "Fault Tolerance Certification",
        "issuer_name": "Resilience Institute",
        "issue_date": "October 07, 2026",
        "recipients": [
            {"name": "Valid Recipient One", "email": "valid1@example.com"},
            {"name": "Faulty Recipient __FAIL_SIMULATION__", "email": "fail@example.com"},
            {"name": "Valid Recipient Two", "email": "valid2@example.com"},
        ]
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Retrieve processed job status
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    job_data = status_resp.json()

    # Verify overall status is PARTIALLY_COMPLETED
    assert job_data["status"] == "PARTIALLY_COMPLETED"
    assert job_data["total_count"] == 3
    assert job_data["processed_count"] == 3
    assert job_data["success_count"] == 2
    assert job_data["failure_count"] == 1
    assert job_data["progress_percentage"] == 100.0

    certs = job_data["certificates"]
    assert len(certs) == 3

    # Check recipient 1 (Valid)
    assert certs[0]["recipient_name"] == "Valid Recipient One"
    assert certs[0]["status"] == "SUCCESS"
    assert certs[0]["download_url"] is not None
    assert certs[0]["error_message"] is None

    # Check recipient 2 (Failed)
    assert certs[1]["recipient_name"] == "Faulty Recipient __FAIL_SIMULATION__"
    assert certs[1]["status"] == "FAILED"
    assert certs[1]["download_url"] is None
    assert certs[1]["error_message"] is not None
    assert "Simulated generation failure" in certs[1]["error_message"]

    # Check recipient 3 (Valid - generated despite previous failure)
    assert certs[2]["recipient_name"] == "Valid Recipient Two"
    assert certs[2]["status"] == "SUCCESS"
    assert certs[2]["download_url"] is not None
    assert certs[2]["error_message"] is None

    # Verify ZIP download still packages the 2 successful certificates
    zip_resp = client.get(f"/api/v1/jobs/{job_id}/download-zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    # Verify zip contents
    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        assert any("Valid_Recipient_One" in name for name in namelist)
        assert any("Valid_Recipient_Two" in name for name in namelist)
        assert not any("Faulty_Recipient" in name for name in namelist)
