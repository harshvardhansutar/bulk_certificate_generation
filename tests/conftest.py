import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as app_database
import app.services.processor as app_processor
from app.config import settings
from app.database import Base, get_db
from app.main import app

# Create a temporary directory for test storage
TEST_TEMP_DIR = Path(tempfile.mkdtemp(prefix="cert_test_"))
TEST_DB_PATH = TEST_TEMP_DIR / "test.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch SessionLocal across modules to use test engine
app_database.engine = test_engine
app_database.SessionLocal = TestingSessionLocal
app_processor.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Override settings for tests
    settings.STORAGE_DIR = TEST_TEMP_DIR / "certificates"
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATABASE_URL = TEST_DATABASE_URL

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    yield

    # Teardown: remove temp directory
    shutil.rmtree(TEST_TEMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_database():
    """Ensure database tables are cleared before each test."""
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client():
    """Provides a FastAPI test client with the test DB injected."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
