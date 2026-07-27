from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ─── Sub-objects ──────────────────────────────────────────────────────────────

class FileUsed(BaseModel):
    name: str
    mode: str           # READ | WRITE | UPDATE | DELETE
    description: str


class BusinessRule(BaseModel):
    rule: str
    line_ref: str
    description: str


# ─── Documentation result ─────────────────────────────────────────────────────

class DocumentationResultOut(BaseModel):
    summary: Optional[str]
    call_flow_diagram: Optional[str]
    data_flow_diagram: Optional[str]
    files_used: Optional[List[FileUsed]]
    business_rules: Optional[List[BusinessRule]]

    model_config = {"from_attributes": True}


# ─── Source file ──────────────────────────────────────────────────────────────

class SourceFileOut(BaseModel):
    id: int
    filename: str
    language: Optional[str]
    size_bytes: int

    model_config = {"from_attributes": True}


# ─── Job ──────────────────────────────────────────────────────────────────────

class JobOut(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    error: Optional[str]
    files: List[SourceFileOut]
    docs: Optional[DocumentationResultOut]

    model_config = {"from_attributes": True}


class JobCreatedOut(BaseModel):
    job_id: UUID
    status: str
    files: List[str]
