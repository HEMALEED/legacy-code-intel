"""
Celery worker.

Start with:
    celery -A celery_worker worker --loglevel=info
"""
from __future__ import annotations

import logging

from celery import Celery
from celery.exceptions import MaxRetriesExceededError

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "lcip",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"


@celery_app.task(name="run_doc_agent_task", bind=True, max_retries=2)
def run_doc_agent_task(self, job_id: str) -> None:
    """
    Pull each source file for the job, run the documentation agent,
    persist the result, and update job status.
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import Job, JobStatus, DocumentationResult, SourceFile
    from app.storage import read_file_sync
    from app.agent.doc_agent import run_documentation_agent

    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.processing
        db.commit()

        # For Track 1: process the FIRST source file.
        # Multi-file support (one result per file) is a Track 2 enhancement.
        source_file: SourceFile | None = job.files[0] if job.files else None
        if source_file is None:
            job.status = JobStatus.failed
            job.error = "No source files attached to job."
            db.commit()
            return

        source_bytes = read_file_sync(source_file.storage_key)
        source_text  = source_bytes.decode("utf-8", errors="replace")

        agent_result = run_documentation_agent(source_file.filename, source_text)

        if agent_result.get("error"):
            job.status = JobStatus.failed
            job.error  = agent_result["error"]
            db.commit()
            return

        # Persist documentation result
        doc = DocumentationResult(
            job_id           = job_id,
            summary          = agent_result.get("summary", ""),
            call_flow_diagram= agent_result.get("call_flow_diagram", ""),
            data_flow_diagram= agent_result.get("data_flow_diagram", ""),
            files_used       = agent_result.get("files_used", []),
            business_rules   = agent_result.get("business_rules", []),
            raw_agent_output = {
                k: v for k, v in agent_result.items()
                if k not in ("source", "chunks")  # don't store large text blobs twice
            },
        )
        db.add(doc)

        # Update language on the source file row
        source_file.language = agent_result.get("language", "")

        job.status = JobStatus.completed
        db.commit()

    except Exception as exc:
        logger.exception("run_doc_agent_task failed for job %s: %s", job_id, exc)
        db.rollback()
        try:
            # Re-fetch in a clean state after rollback
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.failed
                job.error  = str(exc)
                db.commit()
        except Exception:
            logger.exception("Could not update job status to failed for job %s", job_id)
        finally:
            db.close()
        try:
            raise self.retry(exc=exc, countdown=10)
        except MaxRetriesExceededError:
            # Max retries hit — job is already marked failed above, just return
            logger.error("Max retries exceeded for job %s", job_id)
    else:
        db.close()
