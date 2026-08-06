"""
Jobs router — handles:
  POST   /api/jobs                            upload files or ZIP, create job, enqueue agent
  GET    /api/jobs                            list all jobs (newest first)
  GET    /api/jobs/{job_id}                   get job + documentation result
  GET    /api/jobs/{job_id}/source/{file_id}  return raw source file content as plain text
  DELETE /api/jobs/{job_id}                   delete a job and its uploaded files from disk
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job, JobStatus, SourceFile
from app.schemas import JobCreatedOut, JobOut
from app.storage import make_storage_key, save_file, delete_job_files, read_file_sync

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Allowed extensions (lower-case without dot)
ALLOWED_EXTENSIONS = {
    "rpg", "rpgle", "sqlrpgle",
    "cbl", "cob", "cobol",
    "clp", "clle",
    "dds", "pf", "lf", "prtf", "dspf",
    "bnd", "srvpgm",
}


def _allowed(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS or ext == "zip"


def _validate_size(size: int) -> None:
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_bytes // 1_048_576} MB limit.",
        )


async def _collect_files(uploads: List[UploadFile]) -> list[tuple[str, bytes]]:
    """
    Return a flat list of (filename, bytes) pairs.
    ZIP archives are expanded; individual source files are kept as-is.
    """
    collected: list[tuple[str, bytes]] = []

    for upload in uploads:
        raw = await upload.read()
        _validate_size(len(raw))

        fname = upload.filename or "unknown"

        if fname.lower().endswith(".zip"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(raw))
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail=f"{fname} is not a valid ZIP.")
            for info in zf.infolist():
                if info.is_dir():
                    continue
                member_name = Path(info.filename).name
                if _allowed(member_name):
                    collected.append((member_name, zf.read(info.filename)))
            zf.close()
        else:
            if not _allowed(fname):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {fname}. "
                           f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))} or .zip",
                )
            collected.append((fname, raw))

    if not collected:
        raise HTTPException(status_code=400, detail="No supported source files found in upload.")

    return collected


@router.post("", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or more source files (or a ZIP) and start a documentation job."""
    file_pairs = await _collect_files(files)

    # Create job row
    job = Job()
    db.add(job)
    db.flush()  # get job.id before inserting source files

    stored_names: list[str] = []
    for filename, data in file_pairs:
        key = make_storage_key(str(job.id), filename)
        await save_file(key, data)

        source_file = SourceFile(
            job_id=job.id,
            filename=filename,
            storage_key=key,
            size_bytes=len(data),
        )
        db.add(source_file)
        stored_names.append(filename)

    db.commit()
    db.refresh(job)

    # Enqueue Celery task (import here to avoid circular deps at startup)
    from celery_worker import run_doc_agent_task
    run_doc_agent_task.delay(str(job.id))

    return JobCreatedOut(job_id=job.id, status=job.status.value, files=stored_names)


@router.get("", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    """Return all jobs newest-first (no pagination for MVP)."""
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Return a single job with its documentation result if available."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/{job_id}/source/{file_id}")
def get_source_file(job_id: UUID, file_id: int, db: Session = Depends(get_db)):
    """Return the raw source file content as plain text."""
    sf = db.query(SourceFile).filter(
        SourceFile.id == file_id,
        SourceFile.job_id == job_id,
    ).first()
    if sf is None:
        raise HTTPException(status_code=404, detail="Source file not found.")
    try:
        content = read_file_sync(sf.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk.")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content.decode("utf-8", errors="replace"))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Delete a job, its DB rows (cascade), and its uploaded files from disk."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    delete_job_files(str(job_id))
    db.delete(job)
    db.commit()
