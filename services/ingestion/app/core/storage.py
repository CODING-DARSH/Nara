import boto3
from botocore.config import Config
from app.core.config import get_settings

settings = get_settings()
_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _s3_client


def upload_photo(file_bytes: bytes, key: str, content_type: str) -> str:
    """Upload photo to MinIO raw bucket. Returns the object key."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.photo_bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for accessing a photo."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.photo_bucket, "Key": key},
        ExpiresIn=expires_in,
    )

