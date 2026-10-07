import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import CertificateRecord, CertificateStatus, Job, JobStatus
from app.services.generator import (
    CertificateGenerationException,
    generate_certificate_pdf,
)

logger = logging.getLogger(__name__)


def process_bulk_job(job_id: str) -> None:
    """
    Background worker function that processes all certificate generation tasks
    for a given Job ID. Ensures fault isolation: one failure does not halt
    other recipients.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for processing.")
            return

        # Mark job as PROCESSING
        job.status = JobStatus.PROCESSING
        db.commit()

        # Job storage subdirectory
        job_dir = settings.STORAGE_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)

        certificates = (
            db.query(CertificateRecord)
            .filter(CertificateRecord.job_id == job_id)
            .order_by(CertificateRecord.sort_index)
            .all()
        )

        for cert in certificates:
            try:
                cert.status = CertificateStatus.PROCESSING
                db.commit()

                # Destination file path
                cert_filename = f"{cert.certificate_code}.pdf"
                output_path = job_dir / cert_filename

                # Generate certificate
                checksum, file_size = generate_certificate_pdf(
                    recipient_name=cert.recipient_name,
                    recipient_email=cert.recipient_email,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    certificate_code=cert.certificate_code,
                    output_path=output_path,
                    template_title=job.template_title,
                    template_subtitle=job.template_subtitle,
                )

                # Update Certificate record on success
                cert.status = CertificateStatus.SUCCESS
                cert.file_path = str(output_path)
                cert.file_size = file_size
                cert.checksum_hash = checksum
                cert.issued_at = datetime.utcnow()
                cert.error_message = None

                job.success_count += 1

            except (CertificateGenerationException, Exception) as exc:
                logger.warning(
                    f"Failed generating certificate for recipient '{cert.recipient_name}' ({cert.id}): {exc}"
                )
                cert.status = CertificateStatus.FAILED
                cert.error_message = str(exc)
                job.failure_count += 1

            finally:
                job.processed_count += 1
                db.commit()

        # Finalize job status
        job.completed_at = datetime.utcnow()
        if job.failure_count == 0:
            job.status = JobStatus.COMPLETED
        elif job.success_count > 0:
            job.status = JobStatus.PARTIALLY_COMPLETED
        else:
            job.status = JobStatus.FAILED

        db.commit()
        logger.info(
            f"Job {job_id} completed: status={job.status.value}, "
            f"success={job.success_count}, failure={job.failure_count}"
        )

    except Exception as e:
        logger.exception(f"Unexpected fatal error while processing job {job_id}: {e}")
        try:
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
