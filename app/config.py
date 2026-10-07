from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Bulk Certificate Generator API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./certificates.db"
    
    # Storage
    BASE_DIR: Path = Path(__file__).resolve().parent
    STORAGE_DIR: Path = BASE_DIR / "storage" / "certificates"
    
    # Processing & Limits
    MAX_BATCH_SIZE: int = 5000
    DEFAULT_PAGE_SIZE: int = 50
    BASE_URL: str = "http://localhost:8000"
    
    # Error simulation trigger for integration testing
    FAIL_SIMULATION_FLAG: str = "__FAIL_SIMULATION__"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()

# Ensure storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
