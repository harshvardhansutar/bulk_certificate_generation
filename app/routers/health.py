from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["System"])


@router.get("/health", summary="Service health check")
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    storage_writable = settings.STORAGE_DIR.exists() and os_access_check(settings.STORAGE_DIR)

    return {
        "status": "healthy" if db_status == "healthy" and storage_writable else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
        "storage": "writable" if storage_writable else "error",
    }


def os_access_check(path) -> bool:
    import os
    return os.access(str(path), os.W_OK)
