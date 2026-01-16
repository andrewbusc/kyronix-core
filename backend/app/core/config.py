from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Kyronix Core"
    employer_legal_name: str = "Kyronix LLC"
    base_url: str = "https://core.kyronix.ai"
    time_zone: str = "America/Los_Angeles"
    document_output_format: str = "pdf"
    environment: str = "development"
    company_address: str = "28 Geary St Suite 650 San Francisco, CA 94108"
    payroll_contact_email: str = "hr@kyronix.ai"
    verification_signer_name: str = "Sandra Morrow"
    verification_signer_credentials: str = "PHR, SHRM-CP"
    verification_signer_title: str = "HR Manager"
    verification_signer_email: str = "sandra.morrow@kyronix.ai"
    verification_phone: str = "855-912-9883"
    verification_fax: str = "855-912-9392"
    verification_footer_address: str = "28 Geary St. Suite 650 * San Francisco, CA 94108"

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
