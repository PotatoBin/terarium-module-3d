"""Pydantic schemas used by the API."""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    name: str = Field(..., description="Character name")
    description: Optional[str] = Field(None, description="Character description")


class JobResponse(BaseModel):
    character_id: str
    job_id: str
    mesh_path: str
    rig_path: str
    texture_path: str
    preview_path: str


class CharacterResponse(BaseModel):
    character_id: str
    name: Optional[str]
    description: Optional[str]
    updated_at: Optional[str]
    latest_job: Optional[str]
    metadata: Dict[str, str] = Field(default_factory=dict)
