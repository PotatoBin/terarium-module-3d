"""Application configuration management."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Server runtime settings."""

    data_root: Path = Path(os.environ.get("DATA_ROOT", "/data"))
    drawing_spinup_root: Path = Path(os.environ.get("DRAWING_SPINUP_ROOT", "DrawingSpinUp"))
    gpu_ids: List[str] | None = None
    max_concurrent_jobs: int = int(os.environ.get("MAX_CONCURRENT_JOBS", "4"))

    class Config:
        env_prefix = "SERVER_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("gpu_ids", pre=True)
    def parse_gpu_ids(cls, value):  # type: ignore[override]
        if value in (None, "", [], ()):  # pragma: no cover - simple guard
            return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = [item.strip() for item in value.split(",") if item.strip()]
        else:
            parsed = value
        return parsed


settings = Settings()
