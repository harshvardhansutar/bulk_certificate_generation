import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    event_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=False)
    template_title = Column(String(255), default="Certificate of Achievement")
    template_subtitle = Column(String(255), default="is proudly presented to")

    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    total_count = Column(Integer, default=0, nullable=False)
    processed_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    certificates = relationship(
        "CertificateRecord",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CertificateRecord.sort_index"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "event_name": self.event_name,
            "issuer_name": self.issuer_name,
            "issue_date": self.issue_date,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "progress_percentage": round((self.processed_count / self.total_count * 100), 2) if self.total_count > 0 else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CertificateRecord(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    sort_index = Column(Integer, default=0, nullable=False)

    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)

    status = Column(
        Enum(CertificateStatus),
        default=CertificateStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum_hash = Column(String(64), nullable=True)

    issued_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="certificates")

    __table_args__ = (
        Index("idx_cert_job_status", "job_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "certificate_code": self.certificate_code,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "status": self.status.value if isinstance(self.status, CertificateStatus) else self.status,
            "error_message": self.error_message,
            "file_size": self.file_size,
            "checksum_hash": self.checksum_hash,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "download_url": f"/api/v1/certificates/{self.id}/download" if self.status == CertificateStatus.SUCCESS else None,
            "verify_url": f"/api/v1/certificates/verify/{self.certificate_code}" if self.status == CertificateStatus.SUCCESS else None,
        }
