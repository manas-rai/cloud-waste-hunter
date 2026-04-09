"""
Application Configuration
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_parse_none_str="",
    )

    # App
    APP_NAME: str = "Cloud Waste Hunter"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS - Store as string first, then parse
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string to list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [
                origin.strip()
                for origin in self.CORS_ORIGINS.split(",")
                if origin.strip()
            ]
        return self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else []

    # Database
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/cloud_waste_hunter"
    )

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SESSION_TOKEN: str = ""  # Optional, for temporary credentials

    # Detection Thresholds
    EC2_IDLE_CPU_THRESHOLD: float = 5.0  # Percentage
    EC2_IDLE_DAYS: int = 7
    EBS_UNATTACHED_DAYS: int = 30
    SNAPSHOT_AGE_DAYS: int = 90
    NAT_GATEWAY_IDLE_BYTES_THRESHOLD: int = 1_000_000_000  # 1 GB
    NAT_GATEWAY_LOOKBACK_DAYS: int = 7

    # Safety Settings
    DRY_RUN_ENABLED: bool = True
    AUTO_APPROVE_ENABLED: bool = False
    ROLLBACK_RETENTION_DAYS: int = 7

    # ML Settings
    ISOLATION_FOREST_CONTAMINATION: float = 0.1  # Expected proportion of outliers
    ML_MODEL_RETRAIN_INTERVAL_HOURS: int = 24

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
