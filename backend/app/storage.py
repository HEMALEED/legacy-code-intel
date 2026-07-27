"""
File store abstraction.

MVP uses local disk.  Swap STORAGE_BACKEND=s3 in .env to use S3 without
changing any caller code.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import aiofiles

from app.config import settings


def _local_root() -> Path:
    p = Path(settings.storage_local_root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_storage_key(job_id: str, filename: str) -> str:
    """Return a unique storage key for a file."""
    ext = Path(filename).suffix
    return f"{job_id}/{uuid.uuid4().hex}{ext}"


async def save_file(storage_key: str, data: bytes) -> None:
    if settings.storage_backend == "local":
        dest = _local_root() / storage_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as fh:
            await fh.write(data)
    else:
        raise NotImplementedError("S3 backend not yet wired — set STORAGE_BACKEND=local for MVP")


def read_file_sync(storage_key: str) -> bytes:
    """Synchronous read used by Celery worker."""
    if settings.storage_backend == "local":
        return (Path(settings.storage_local_root) / storage_key).read_bytes()
    raise NotImplementedError("S3 backend not yet wired — set STORAGE_BACKEND=local for MVP")
