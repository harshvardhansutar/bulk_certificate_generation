import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateRecord, CertificateStatus, Job, JobStatus
from app.schemas import (
    CreateJobRequest,
    JobCreateResponse,
    JobListResponse,
    JobProgressResponse,
)
from app.services.processor import process_bulk_job
from app.services.zip_service import create_job_certificates_zip, sanitize_filename

router = APIRouter(prefix="/api/v1/jobs", tags=["Certificate Jobs"])


def generate_unique_certificate_code(index: int) -> str:
    """Generate human-readable unique verification code: CERT-YYYY-RANDOM"""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"CERT-{unique_suffix}"


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a bulk certificate generation job",
    description="Accepts event details and a list of recipients. Enqueues generation in the background and returns job ID.",
)
def create_bulk_generation_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    job_title = request.title or f"{request.event_name} Certificates"
    from datetime import date
    issue_date = request.issue_date.strip() if request.issue_date and request.issue_date.strip() else date.today().strftime("%B %d, %Y")

    # Create master Job record
    job = Job(
        id=job_id,
        title=job_title,
        event_name=request.event_name,
        issuer_name=request.issuer_name,
        issue_date=issue_date,
        template_title=request.template_title or "Certificate of Achievement",
        template_subtitle=request.template_subtitle or "is proudly presented to",
        status=JobStatus.PENDING,
        total_count=len(request.recipients),
        processed_count=0,
        success_count=0,
        failure_count=0,
    )
    db.add(job)

    # Pre-create recipient certificate records
    for idx, recipient in enumerate(request.recipients):
        cert = CertificateRecord(
            id=str(uuid.uuid4()),
            job_id=job_id,
            certificate_code=generate_unique_certificate_code(idx),
            sort_index=idx,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            status=CertificateStatus.PENDING,
        )
        db.add(cert)

    db.commit()
    db.refresh(job)

    # Dispatch to background task processing
    background_tasks.add_task(process_bulk_job, job_id)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_count,
        message="Bulk certificate generation job accepted and processing in background.",
        status_url=f"/api/v1/jobs/{job.id}",
        created_at=job.created_at,
    )


@router.get(
    "/{job_id}",
    response_model=JobProgressResponse,
    summary="Track job progress and status",
    description="Returns current generation progress, counts, overall status, and list of recipient certificates.",
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    progress_percentage = (
        round((job.processed_count / job.total_count * 100), 2)
        if job.total_count > 0
        else 0.0
    )

    zip_url = (
        f"/api/v1/jobs/{job.id}/download-zip"
        if job.success_count > 0
        else None
    )

    certs_data = [cert.to_dict() for cert in job.certificates]

    return {
        **job.to_dict(),
        "progress_percentage": progress_percentage,
        "zip_download_url": zip_url,
        "certificates": certs_data,
    }


@router.get(
    "",
    response_model=JobListResponse,
    summary="List all certificate generation jobs",
    description="Returns paginated list of all submitted jobs.",
)
def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    total_jobs = db.query(Job).count()
    jobs = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    results = []
    for job in jobs:
        progress_percentage = (
            round((job.processed_count / job.total_count * 100), 2)
            if job.total_count > 0
            else 0.0
        )
        zip_url = (
            f"/api/v1/jobs/{job.id}/download-zip"
            if job.success_count > 0
            else None
        )
        job_dict = job.to_dict()
        job_dict["progress_percentage"] = progress_percentage
        job_dict["zip_download_url"] = zip_url
        job_dict["certificates"] = None  # Don't embed full lists in index view for performance
        results.append(job_dict)

    return JobListResponse(
        total_jobs=total_jobs,
        page=page,
        page_size=page_size,
        jobs=results,
    )


@router.get(
    "/{job_id}/download-zip",
    summary="Download all certificates as a ZIP archive",
    description="Bundles all successfully generated certificates in this job into a single downloadable .zip file.",
)
def download_job_certificates_zip(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    if job.success_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No successfully generated certificates are available to download for this job yet.",
        )

    try:
        zip_buffer = create_job_certificates_zip(db, job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    safe_event = sanitize_filename(job.event_name)
    zip_filename = f"{safe_event}_certificates_{job.id[:8]}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        },
    )
