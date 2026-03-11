import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict

# Debug: Print all environment variables
print("DEBUG: All environment variables:", file=sys.stderr)
for key, value in os.environ.items():
    if 'DATABASE' in key or 'POSTGRES' in key:
        print(f"  {key} = {value[:50] if value else 'EMPTY'}...", file=sys.stderr)


class Settings(BaseSettings):
    project_name: str = "Kyronix Core"
    employer_legal_name: str = "Kyronix LLC"
    verification_employer_display_name: str = "Northline Premier"
    verification_employer_former_name: str = "Kyronix LLC"
    verification_brand_subtitle: str = "Business Management"
    verification_website: str = "northlinepremier.com"
    verification_generated_from_host: str = "core.northlinepremier.com"
    base_url: str = "https://core.kyronix.ai"
    time_zone: str = "America/Los_Angeles"
    document_output_format: str = "pdf"
    environment: str = "development"
    company_address: str = "28 Geary St Suite 650 San Francisco, CA 94108"
    payroll_contact_email: str = "hr@northlinepremier.com"
    verification_signer_name: str = "Sandra Morrow"
    verification_signer_credentials: str = "PHR, SHRM-CP"
    verification_signer_title: str = "HR Manager"
    verification_signer_email: str = "hr@northlinepremier.com"
    verification_email_signature_name: str = "Sandra Morrow"
    verification_email_signature_title: str = "HR Coordinator/ Administration"
    verification_phone: str = "855-912-9883"
    verification_fax: str = "855-912-9392"
    verification_footer_address: str = "28 Geary St. Suite 650 * San Francisco, CA 94108"
    verification_logo_path: str | None = None
    verification_body_font_path: str | None = None
    verification_signature_font_path: str | None = None

    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://kyronix:kyronix@db:5432/kyronix_core")
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    password_reset_expire_minutes: int = 60

    default_admin_email: str = "admin@northlinepremier.com"
    default_admin_password: str = "ChangeMeNow"

    allow_origins: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_from_email: str = "hr@northlinepremier.com"
    smtp_from_name: str = "Northline Premier HR"

    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_endpoint_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
