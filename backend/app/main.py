from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers.jobs import router as jobs_router
from app.routers.chat import router as chat_router

# Create all tables on startup (fine for MVP; use Alembic for prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LegacyLens — IBM i Documentation Platform",
    description="AI-powered documentation for RPG, COBOL, CLP, and DDS source code.",
    version="2.0.0",
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
