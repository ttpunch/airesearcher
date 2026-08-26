"""S3-compatible object storage client (MinIO in dev, S3 in prod — same API).

Sync boto3 client wrapped for async callers via asyncio.to_thread, rather
than pulling in a separate async S3 library — one client, one code path,
consistent with this project's "start simple" bias elsewhere.
"""

import asyncio
import hashlib
from dataclasses import dataclass

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)


@dataclass
class StoredObject:
    storage_path: str
    content_hash: str
    size: int


def _put_object_sync(key: str, content: bytes, content_type: str) -> StoredObject:
    client = _client()
    content_hash = hashlib.sha256(content).hexdigest()
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type)
    return StoredObject(storage_path=key, content_hash=content_hash, size=len(content))


async def put_object(key: str, content: bytes, content_type: str) -> StoredObject:
    return await asyncio.to_thread(_put_object_sync, key, content, content_type)


def _get_object_sync(key: str) -> bytes:
    client = _client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()


async def get_object(key: str) -> bytes:
    return await asyncio.to_thread(_get_object_sync, key)
