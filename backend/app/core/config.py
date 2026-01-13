from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Kyronix Core"
    employer_legal_name: str = "Kyronix LLC"
    base_url: str = "https://core.kyronix.ai"
    time_zone: str = "America/Los_Angeles"
    document_output_format: str = "pdf"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://kyronix:kyronix@db:5432/kyronix_core"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    password_reset_expire_minutes: int = 60

    default_admin_email: str = "admin@kyronix.ai"
    default_admin_password: str = "ChangeMeNow"

    allow_origins: str = "http://localhost:5173"

    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_endpoint_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
