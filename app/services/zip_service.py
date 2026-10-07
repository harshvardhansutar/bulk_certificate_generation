import io
import re
import zipfile
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.models import CertificateRecord, CertificateStatus, Job


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filename usage."""
    return re.sub(r"[^\w\-.]", "_", name.strip())


def create_job_certificates_zip(db: Session, job: Job) -> io.BytesIO:
    """
    Creates a ZIP archive in-memory containing all successfully generated
    certificates for the given job.
    """
    successful_certs: List[CertificateRecord] = (
        db.query(CertificateRecord)
        .filter(
            CertificateRecord.job_id == job.id,
            CertificateRecord.status == CertificateStatus.SUCCESS,
        )
        .all()
    )

    if not successful_certs:
        raise ValueError("No successfully generated certificates found for this job.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cert in successful_certs:
            if cert.file_path and Path(cert.file_path).exists():
                file_path = Path(cert.file_path)
                safe_name = sanitize_filename(cert.recipient_name)
                zip_filename = f"{safe_name}_{cert.certificate_code}.pdf"
                zf.write(file_path, arcname=zip_filename)

    zip_buffer.seek(0)
    return zip_buffer
