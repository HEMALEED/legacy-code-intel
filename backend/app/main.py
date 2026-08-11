import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers.jobs import router as jobs_router
from app.routers.chat import router as chat_router

logger = logging.getLogger(__name__)


def _requeue_stuck_jobs() -> None:
    """
    On startup, find any jobs still in 'queued' or 'processing' state
    (left over from a previous crash/restart) and re-send them to Celery.
    """
    from app.database import SessionLocal
    from app.models import Job, JobStatus
    from celery_worker import run_doc_agent_task

    db = SessionLocal()
    try:
        stuck = db.query(Job).filter(
            Job.status.in_([JobStatus.queued, JobStatus.processing])
        ).all()
        if stuck:
            logger.info("Requeueing %d stuck job(s) from previous run…", len(stuck))
        for job in stuck:
            job.status = JobStatus.queued
            db.commit()
            run_doc_agent_task.delay(str(job.id))
            logger.info("  → requeued job %s", job.id)
    except Exception:
        logger.exception("Failed to requeue stuck jobs on startup")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (fine for MVP; use Alembic for prod)
    Base.metadata.create_all(bind=engine)
    _requeue_stuck_jobs()
    yield


app = FastAPI(
    title="LegacyLens — IBM i Documentation Platform",
    description="AI-powered documentation for RPG, COBOL, CLP, and DDS source code.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}
