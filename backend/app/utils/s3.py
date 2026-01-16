from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3ConfigError(RuntimeError):
    pass


def _build_client_kwargs() -> dict:
    kwargs: dict = {}
    if settings.s3_region:
        kwargs["region_name"] = settings.s3_region
    if settings.s3_access_key_id and settings.s3_secret_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return kwargs


@lru_cache(maxsize=1)
def get_s3_client():
    if not settings.s3_bucket:
        raise S3ConfigError("S3 bucket is not configured")
    return boto3.client("s3", **_build_client_kwargs())


def upload_pdf_bytes(key: str, content: bytes, metadata: dict | None = None) -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=content,
            ContentType="application/pdf",
            Metadata=metadata or {},
        )
    except ClientError as exc:
        raise S3ConfigError(f"Failed to upload PDF to S3: {exc}") from exc


def download_pdf_bytes(key: str) -> bytes:
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.s3_bucket, Key=key)
        body = response.get("Body")
        return body.read() if body else b""
    except ClientError as exc:
        raise S3ConfigError(f"Failed to download PDF from S3: {exc}") from exc


def delete_pdf_bytes(key: str) -> None:
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        raise S3ConfigError(f"Failed to delete PDF from S3: {exc}") from exc
