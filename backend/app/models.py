import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    queued     = "queued"
    processing = "processing"
    completed  = "completed"
    failed     = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status     = Column(Enum(JobStatus), nullable=False, default=JobStatus.queued)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    error      = Column(Text, nullable=True)

    files = relationship("SourceFile", back_populates="job", cascade="all, delete-orphan")
    docs  = relationship("DocumentationResult", back_populates="job",
                         cascade="all, delete-orphan", uselist=False)


class SourceFile(Base):
    __tablename__ = "source_files"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    job_id      = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    filename    = Column(String(255), nullable=False)
    language    = Column(String(32), nullable=True)   # RPG | RPGLE | COBOL | CLP | CLLE | DDS | …
    storage_key = Column(String(512), nullable=False) # disk path or S3 key
    size_bytes  = Column(Integer, nullable=False)

    job = relationship("Job", back_populates="files")


class DocumentationResult(Base):
    __tablename__ = "documentation_results"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    job_id     = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"),
                        nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    # Agent step outputs
    summary           = Column(Text, nullable=True)       # plain-English summary
    call_flow_diagram = Column(Text, nullable=True)       # Mermaid source
    data_flow_diagram = Column(Text, nullable=True)       # Mermaid source
    files_used        = Column(JSON, nullable=True)       # [{name, mode, description}]
    business_rules    = Column(JSON, nullable=True)       # [{rule, line_ref, description}]
    observations      = Column(JSON, nullable=True)       # [{finding, line_ref, severity}]
    raw_agent_output  = Column(JSON, nullable=True)       # full state for debugging

    job = relationship("Job", back_populates="docs")
