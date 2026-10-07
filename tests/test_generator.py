from pathlib import Path
import pytest
from app.services.generator import (
    CertificateGenerationException,
    compute_sha256,
    generate_certificate_pdf,
)


def test_generator_creates_valid_pdf(tmp_path: Path):
    output_pdf = tmp_path / "cert_test.pdf"
    
    checksum, file_size = generate_certificate_pdf(
        recipient_name="Alexander Hamilton",
        recipient_email="alex@example.com",
        event_name="Constitutional Law Summit",
        issuer_name="Treasury Academy",
        issue_date="October 07, 2026",
        certificate_code="CERT-ALEX-001",
        output_path=output_pdf,
    )
    
    assert output_pdf.exists()
    assert file_size > 0
    assert len(checksum) == 64  # SHA-256 is 64 hex characters
    assert compute_sha256(output_pdf) == checksum
    
    # Verify PDF magic bytes
    with open(output_pdf, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_generator_simulated_failure_handling(tmp_path: Path):
    output_pdf = tmp_path / "cert_fail.pdf"
    
    with pytest.raises(CertificateGenerationException) as exc_info:
        generate_certificate_pdf(
            recipient_name="Faulty Recipient __FAIL_SIMULATION__",
            recipient_email="test@example.com",
            event_name="Failing Event",
            issuer_name="Academy",
            issue_date="October 07, 2026",
            certificate_code="CERT-FAIL-001",
            output_path=output_pdf,
        )
    
    assert "Simulated generation failure" in str(exc_info.value)
    # Output file should not linger
    assert not output_pdf.exists()
