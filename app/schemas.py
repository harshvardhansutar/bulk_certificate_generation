import re
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models import JobStatus, CertificateStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class RecipientInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Full name of recipient")
    email: str = Field(..., description="Valid recipient email address")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Recipient name cannot be empty or only whitespace")
        return stripped

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not EMAIL_REGEX.match(stripped):
            raise ValueError(f"Invalid email address format: '{v}'")
        return stripped


class CreateJobRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Optional job title")
    event_name: str = Field(..., min_length=1, max_length=255, description="Name of event or course")
    issuer_name: str = Field(..., min_length=1, max_length=255, description="Organization or authority issuing the certificate")
    issue_date: Optional[str] = Field(None, description="Issue date in YYYY-MM-DD or readable format (default: today)")
    template_title: Optional[str] = Field("Certificate of Achievement", description="Main certificate title")
    template_subtitle: Optional[str] = Field("is proudly presented to", description="Subtitle text preceding recipient name")
    recipients: List[RecipientInput] = Field(..., min_length=1, description="List of recipients")

    @field_validator("event_name", "issuer_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_recipients: int
    message: str
    status_url: str
    created_at: datetime


class CertificateSummary(BaseModel):
    id: str
    certificate_code: str
    recipient_name: str
    recipient_email: str
    status: CertificateStatus
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    checksum_hash: Optional[str] = None
    issued_at: Optional[datetime] = None
    download_url: Optional[str] = None
    verify_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobProgressResponse(BaseModel):
    id: str
    title: str
    event_name: str
    issuer_name: str
    issue_date: str
    status: JobStatus
    total_count: int
    processed_count: int
    success_count: int
    failure_count: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    zip_download_url: Optional[str] = None
    certificates: Optional[List[CertificateSummary]] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    total_jobs: int
    page: int
    page_size: int
    jobs: List[JobProgressResponse]


class CertificateVerifyResponse(BaseModel):
    valid: bool
    certificate_code: str
    recipient_name: Optional[str] = None
    event_name: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[str] = None
    issued_at: Optional[datetime] = None
    checksum_hash: Optional[str] = None
    message: str
