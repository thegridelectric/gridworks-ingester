from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

class IngesterSettings(BaseSettings):
    """Configuration for GridWorks Ingester"""
    
    # MQTT Settings
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None

    # PostgreSQL Settings
    postgres_enabled: bool = True
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "journalkeeper"
    postgres_user: str = "gridworks"
    postgres_password: str = "gridworks"
    
    # S3 Settings
    s3_enabled: bool = True
    s3_bucket: str = "telemetry"
    s3_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Local Storage
    local_storage_enabled: bool = True
    local_storage_path: Path = Path("/var/gridworks/ingester/data")
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # or "console"
    
    model_config = SettingsConfigDict(
        env_prefix="GWI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )