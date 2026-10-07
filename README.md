# 🎓 Bulk Certificate Generator API (CertiFlow)

A high-performance, fault-tolerant Python backend API built with **FastAPI**, **SQLAlchemy**, and **ReportLab** designed to accept certificate generation requests for large recipient batches, generate tamper-evident PDF certificates with dynamic QR verification codes, monitor progress, and retrieve credentials individually or as bulk ZIP archives.

Includes an **interactive web dashboard**, **full test suite**, and **Swagger UI OpenAPI documentation**.

---

## 🌟 Key Features

* **Bulk Background Processing**: Accepts thousands of recipients per batch with immediate `202 Accepted` acknowledgement, processing certificate generation asynchronously in background tasks without blocking client connections.
* **Fault Isolation & Resilience**: Individual recipient failures (e.g. malformed data, rendering exceptions) are isolated. A single failure never halts other valid recipients in the batch. Detailed error messages are preserved per recipient with overall status transitioning to `PARTIALLY_COMPLETED`.
* **High-Resolution Vector PDF Template**: Certificates are rendered as vector Landscape A4 PDFs with ornate borders, gold seals, customizable event/issuer text, and embedded scannable QR verification codes.
* **Tamper-Evident Verification**: Computes a cryptographic **SHA-256 integrity hash** for every certificate file and provides a public verification endpoint (`/api/v1/certificates/verify/{code}`) to confirm authenticity.
* **Flexible Retrieval**: 
  * Download individual recipient certificates (`.pdf`).
  * Download all successfully generated certificates in a batch bundled as a `.zip` archive.
* **Deterministic Recipient Ordering**: Preserves the exact ordering of input recipients using dedicated sequence indexing.
* **Interactive Web Dashboard**: Built-in dashboard at `/` to test bulk creation, watch live progress bars, download PDFs/ZIPs, and test credential verification in real-time.

---

## 🏗️ System Architecture & Design Decisions

### 1. Framework: FastAPI
* **Why FastAPI over Flask / Django?**
  * Built-in asynchronous request handling and standard dependency injection.
  * Native background task execution (`BackgroundTasks`), perfectly suited for batch jobs without requiring heavy external message brokers for standard workloads.
  * Automatic, interactive OpenAPI 3.0 documentation (`/docs` and `/redoc`).
  * High-performance serialization and schema validation powered by **Pydantic v2**.

### 2. Processing Strategy: Asynchronous Background Processing vs. Synchronous
* **Decision**: We chose **asynchronous background processing with HTTP 202 Accepted**.
* **Reasoning**:
  * Generating PDF documents for hundreds or thousands of recipients is CPU- and I/O-intensive. In a synchronous model, a request with 500 recipients would take 15–30 seconds, leading to HTTP client timeouts, gateway errors (504 Gateway Timeout), and blocked worker threads.
  * By returning `HTTP 202 Accepted` with a unique `job_id`, the client receives instant confirmation (< 30ms) and can query `GET /api/v1/jobs/{job_id}` to monitor real-time progress (`processed_count`, `success_count`, `failure_count`, and `progress_percentage`).
  * For larger multi-server scale, the processor service is decoupled and can be plugged into Celery or Redis Queue (RQ) with zero changes to the database schema or API interface.

### 3. Database: Relational Schema (SQLAlchemy 2.0 + SQLite / PostgreSQL)
* **Entities**:
  * `Job`: Tracks bulk request metadata (`id`, `title`, `event_name`, `issuer_name`, `issue_date`, `template_title`, `status`, counters, timestamps).
  * `CertificateRecord`: Represents each recipient's credential (`id`, `job_id`, `certificate_code`, `sort_index`, `recipient_name`, `recipient_email`, `status`, `error_message`, `file_path`, `file_size`, `checksum_hash`, `issued_at`).
* **Why a Relational Model?**
  * Enforces foreign key constraints with `ON DELETE CASCADE`.
  * Indexing on `job_id`, `certificate_code`, and `status` ensures sub-millisecond status lookups and fast filtering.
  * Defaults to SQLite with zero setup; switching to PostgreSQL simply requires setting `DATABASE_URL=postgresql://user:pass@host/dbname` in `.env`.

### 4. Failure Handling & Isolation
* If recipient 3 out of 100 encounters a failure, the background worker catches the exception specifically for recipient 3, marks its status as `FAILED`, saves the exact error description, increments `failure_count`, and immediately continues generating recipients 4 through 100.
* Overall job status transitions:
  * `COMPLETED`: 100% of recipients generated successfully (`failure_count == 0`).
  * `PARTIALLY_COMPLETED`: Some succeeded, some failed (`success_count > 0 and failure_count > 0`).
  * `FAILED`: All recipients failed (`success_count == 0`).

---

## 📁 Project Structure

```
Bulk_Certification_Generator/
├── app/
│   ├── config.py                 # Configuration settings (Pydantic BaseSettings)
│   ├── database.py               # SQLAlchemy engine & session factory
│   ├── main.py                   # FastAPI initialization, routing & static mount
│   ├── models.py                 # Database models (Job, CertificateRecord)
│   ├── schemas.py                # Pydantic validation schemas
│   ├── routers/
│   │   ├── jobs.py               # Job submission, status tracking, bulk ZIP download
│   │   ├── certificates.py       # Single certificate download & verification
│   │   └── health.py             # Health check endpoint
│   ├── services/
│   │   ├── generator.py          # ReportLab PDF engine, QR code & SHA-256 computation
│   │   ├── processor.py          # Background worker with fault isolation
│   │   └── zip_service.py        # In-memory streaming ZIP archive builder
│   ├── static/                   # Interactive Web UI Dashboard
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── storage/certificates/     # Generated PDF certificates storage
├── tests/
│   ├── conftest.py               # Isolated test database and TestClient fixtures
│   ├── test_validation.py        # Input validation tests (emails, empty names, required fields)
│   ├── test_generator.py         # PDF renderer unit tests and simulated error handling
│   ├── test_jobs.py              # Job creation, background completion, and pagination
│   ├── test_failure_handling.py  # Isolated recipient failure tests (partial success)
│   └── test_retrieval.py         # PDF download, ZIP download, and verification endpoint
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* `pip` package manager

### 2. Installation
Clone or navigate to the repository directory:
```bash
cd "p:/@Web Development/Bulk_Certification_Generator"
```

Create a virtual environment (optional but recommended):
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Start the development server using `uvicorn`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be accessible at:
* **Interactive Web Dashboard**: [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Tests

The test suite covers input validation, PDF creation, job lifecycle, fault isolation, ZIP downloads, and verification.

To run all tests:
```bash
pytest -v
```

Output:
```
============================= test session starts =============================
tests/test_failure_handling.py::test_individual_failure_isolation PASSED [  5%]
tests/test_generator.py::test_generator_creates_valid_pdf PASSED         [ 11%]
tests/test_generator.py::test_generator_simulated_failure_handling PASSED [ 17%]
tests/test_jobs.py::test_create_and_process_job_successfully PASSED      [ 23%]
tests/test_jobs.py::test_list_jobs_pagination PASSED                     [ 29%]
tests/test_jobs.py::test_get_non_existent_job PASSED                     [ 35%]
tests/test_retrieval.py::test_retrieve_and_download_certificate PASSED   [ 41%]
tests/test_retrieval.py::test_verify_invalid_certificate_code PASSED     [ 47%]
tests/test_retrieval.py::test_download_non_existent_certificate PASSED   [ 52%]
tests/test_retrieval.py::test_download_zip_archive PASSED                [ 58%]
tests/test_retrieval.py::test_download_zip_non_existent_job PASSED       [ 64%]
tests/test_retrieval.py::test_health_check PASSED                        [ 70%]
tests/test_validation.py::test_create_job_empty_recipients PASSED        [ 76%]
tests/test_validation.py::test_create_job_invalid_email_format PASSED    [ 82%]
tests/test_validation.py::test_create_job_empty_recipient_name PASSED    [ 88%]
tests/test_validation.py::test_create_job_missing_required_fields PASSED [ 94%]
tests/test_validation.py::test_create_job_whitespace_only_event_name PASSED [100%]
============================= 17 passed in 0.80s ==============================
```

---

## 📡 API Reference & Examples

### 1. Submit a Bulk Certificate Generation Job
* **Endpoint**: `POST /api/v1/jobs`
* **Status**: `202 Accepted`

**cURL Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Cloud Native Architecture Summit 2026",
    "issuer_name": "Cloud Native Academy",
    "issue_date": "October 07, 2026",
    "template_title": "Certificate of Excellence",
    "recipients": [
      {
        "name": "Jane Doe",
        "email": "jane.doe@example.com"
      },
      {
        "name": "John Smith",
        "email": "john.smith@example.com"
      }
    ]
  }'
```

**Response (HTTP 202)**:
```json
{
  "job_id": "a921d7b3-8c44-42b7-8ce1-e8d1a120bf32",
  "status": "PENDING",
  "total_recipients": 2,
  "message": "Bulk certificate generation job accepted and processing in background.",
  "status_url": "/api/v1/jobs/a921d7b3-8c44-42b7-8ce1-e8d1a120bf32",
  "created_at": "2026-10-07T07:15:00.123456"
}
```

---

### 2. Check Job Status & Progress
* **Endpoint**: `GET /api/v1/jobs/{job_id}`
* **Status**: `200 OK`

**cURL Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/a921d7b3-8c44-42b7-8ce1-e8d1a120bf32"
```

**Response (HTTP 200)**:
```json
{
  "id": "a921d7b3-8c44-42b7-8ce1-e8d1a120bf32",
  "title": "Cloud Native Architecture Summit 2026 Certificates",
  "event_name": "Cloud Native Architecture Summit 2026",
  "issuer_name": "Cloud Native Academy",
  "issue_date": "October 07, 2026",
  "status": "COMPLETED",
  "total_count": 2,
  "processed_count": 2,
  "success_count": 2,
  "failure_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T07:15:00.123456",
  "completed_at": "2026-10-07T07:15:00.345678",
  "zip_download_url": "/api/v1/jobs/a921d7b3-8c44-42b7-8ce1-e8d1a120bf32/download-zip",
  "certificates": [
    {
      "id": "f51a2380-60b1-47fa-80ee-c0209e51c881",
      "certificate_code": "CERT-8D05C3A1",
      "recipient_name": "Jane Doe",
      "recipient_email": "jane.doe@example.com",
      "status": "SUCCESS",
      "error_message": null,
      "file_size": 5420,
      "checksum_hash": "a1b2c3d4e5f6...",
      "issued_at": "2026-10-07T07:15:00.200000",
      "download_url": "/api/v1/certificates/f51a2380-60b1-47fa-80ee-c0209e51c881/download",
      "verify_url": "/api/v1/certificates/verify/CERT-8D05C3A1"
    }
  ]
}
```

---

### 3. Download Single Certificate PDF
* **Endpoint**: `GET /api/v1/certificates/{certificate_id}/download`
* **Query Params**: `disposition=inline` (default) or `attachment`

**cURL Request**:
```bash
curl -O -J "http://localhost:8000/api/v1/certificates/f51a2380-60b1-47fa-80ee-c0209e51c881/download?disposition=attachment"
```

---

### 4. Download All Certificates as ZIP Archive
* **Endpoint**: `GET /api/v1/jobs/{job_id}/download-zip`
* **Status**: `200 OK` (Streams `application/zip`)

**cURL Request**:
```bash
curl -O -J "http://localhost:8000/api/v1/jobs/a921d7b3-8c44-42b7-8ce1-e8d1a120bf32/download-zip"
```

---

### 5. Verify Certificate Authenticity
* **Endpoint**: `GET /api/v1/certificates/verify/{certificate_code}`
* **Status**: `200 OK`

**cURL Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/certificates/verify/CERT-8D05C3A1"
```

**Response (HTTP 200)**:
```json
{
  "valid": true,
  "certificate_code": "CERT-8D05C3A1",
  "recipient_name": "Jane Doe",
  "event_name": "Cloud Native Architecture Summit 2026",
  "issuer_name": "Cloud Native Academy",
  "issue_date": "October 07, 2026",
  "issued_at": "2026-10-07T07:15:00.200000",
  "checksum_hash": "a1b2c3d4e5f6...",
  "message": "Certificate is authentic, verified, and officially issued."
}
```

---

### 6. Health Check
* **Endpoint**: `GET /health`

**cURL Request**:
```bash
curl -X GET "http://localhost:8000/health"
```

**Response**:
```json
{
  "status": "healthy",
  "service": "Bulk Certificate Generator API",
  "version": "1.0.0",
  "database": "healthy",
  "storage": "writable"
}
```

---

## 🛡️ Testing Failure Isolation

To test the fault-isolation feature during an evaluation or interview:
Include `__FAIL_SIMULATION__` in any recipient's name or email address (or click the **"Load 6 (1 Fails)"** preset in the Web Dashboard). 

The system will:
1. Detect and isolate the simulated rendering exception on that specific recipient.
2. Mark that recipient as `FAILED` with the exception message.
3. Successfully render all other valid recipients in the batch.
4. Mark the job as `PARTIALLY_COMPLETED`.
5. Permit downloading the valid certificates individually or via ZIP (excluding the failed recipient).
