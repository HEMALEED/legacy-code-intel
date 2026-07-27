from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers.jobs import router as jobs_router

# Create all tables on startup (fine for MVP; use Alembic for prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Legacy Code Intelligence Platform",
    description="AI-powered documentation for RPG, COBOL, CLP, and DDS source code.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
