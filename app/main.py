import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import certificates, health, jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bulk_cert_generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and storage directory is ready
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 🎓 Bulk Certificate Generator API

A high-performance backend API designed for organizations to generate, track, and retrieve bulk digital credentials and certificates.

### Key Capabilities:
* **Bulk Processing**: Submit thousands of recipients in a single batch with non-blocking background workers.
* **Fault Isolation**: Individual recipient rendering failures are caught and tracked without halting the rest of the batch.
* **Real-time Status Tracking**: Detailed metrics (total, processed, successful, failed) and live progress percentage.
* **Tamper-evident Verification**: Automated unique credential codes, QR code embedding, and cryptographic SHA-256 checksums.
* **Flexible Retrieval**: Download individual PDF certificates or all batch certificates bundled in a `.zip` archive.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend and external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(jobs.router)
app.include_router(certificates.router)
app.include_router(health.router)

# Mount static files and Web UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the interactive web dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Bulk Certificate Generator API is running. Visit /docs for Swagger UI."}
