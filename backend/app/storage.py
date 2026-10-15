"""Where uploaded files live: a private S3 bucket in production (FILE_STORAGE_BUCKET), a local folder otherwise.

Keys are opaque ("<uuid>.jpg", "documents/<uuid>.jpg"); callers never build paths themselves.
"""
import os
from functools import lru_cache
from pathlib import Path


def _bucket() -> str | None:
    return os.environ.get("FILE_STORAGE_BUCKET") or None


def local_dir() -> Path:
    default = Path(__file__).resolve().parents[2] / ".local" / "photos"
    path = Path(os.environ.get("PHOTO_STORAGE_DIR") or default)
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def _s3():
    import boto3
    return boto3.client("s3")


def save(key: str, data: bytes, content_type: str) -> None:
    bucket = _bucket()
    if bucket:
        _s3().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256")
        return
    target = local_dir() / key
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(data)
    partial.replace(target)


def load(key: str) -> bytes | None:
    bucket = _bucket()
    if bucket:
        try:
            return _s3().get_object(Bucket=bucket, Key=key)["Body"].read()
        except _s3().exceptions.NoSuchKey:
            return None
    path = local_dir() / key
    return path.read_bytes() if path.is_file() else None


def delete(key: str) -> None:
    bucket = _bucket()
    if bucket:
        _s3().delete_object(Bucket=bucket, Key=key)
    else:
        (local_dir() / key).unlink(missing_ok=True)
