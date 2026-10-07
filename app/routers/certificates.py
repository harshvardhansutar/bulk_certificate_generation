from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateRecord, CertificateStatus, Job
from app.schemas import CertificateSummary, CertificateVerifyResponse
from app.services.zip_service import sanitize_filename

router = APIRouter(prefix="/api/v1/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    response_model=CertificateSummary,
    summary="Get single certificate metadata",
    description="Returns metadata and current status for an individual recipient certificate.",
)
def get_certificate_details(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    cert = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )
    return cert.to_dict()


@router.get(
    "/{certificate_id}/download",
    summary="Download individual certificate PDF",
    description="Streams the generated PDF certificate for this recipient.",
)
def download_certificate(
    certificate_id: str,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
    db: Session = Depends(get_db),
):
    cert = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )

    if cert.status != CertificateStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not ready for download. Current status: {cert.status.value}",
        )

    if not cert.file_path or not Path(cert.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing on storage server",
        )

    safe_name = sanitize_filename(cert.recipient_name)
    download_filename = f"{safe_name}_{cert.certificate_code}.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=download_filename,
        content_disposition_type=disposition,
    )


@router.get(
    "/verify/{certificate_code}",
    response_model=CertificateVerifyResponse,
    summary="Verify certificate authenticity",
    description="Public verification endpoint used by QR code scans or employers to verify the authenticity of a credential.",
)
def verify_certificate(
    certificate_code: str,
    db: Session = Depends(get_db),
):
    cert = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.certificate_code == certificate_code)
        .first()
    )
    if not cert:
        return CertificateVerifyResponse(
            valid=False,
            certificate_code=certificate_code,
            message="Certificate not found or invalid credential identifier.",
        )

    if cert.status != CertificateStatus.SUCCESS:
        return CertificateVerifyResponse(
            valid=False,
            certificate_code=certificate_code,
            message=f"Certificate generation was not completed successfully. Status: {cert.status.value}",
        )

    job = db.query(Job).filter(Job.id == cert.job_id).first()

    return CertificateVerifyResponse(
        valid=True,
        certificate_code=cert.certificate_code,
        recipient_name=cert.recipient_name,
        event_name=job.event_name if job else "N/A",
        issuer_name=job.issuer_name if job else "N/A",
        issue_date=job.issue_date if job else "N/A",
        issued_at=cert.issued_at,
        checksum_hash=cert.checksum_hash,
        message="Certificate is authentic, verified, and officially issued.",
    )
