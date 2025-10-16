"""Character-aware storage utilities."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .config import settings


def characters_root() -> Path:
    root = settings.data_root / "characters"
    root.mkdir(parents=True, exist_ok=True)
    return root


def character_dir(character_id: str) -> Path:
    directory = characters_root() / character_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def job_dir(character_id: str, job_id: str) -> Path:
    directory = character_dir(character_id) / "outputs" / job_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def job_metadata_path(character_id: str, job_id: str) -> Path:
    return job_dir(character_id, job_id) / "metadata.json"


def save_metadata(character_id: str, job_id: str, metadata: Dict) -> None:
    metadata_path = job_metadata_path(character_id, job_id)
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def list_characters() -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for character in characters_root().iterdir():
        if not character.is_dir():
            continue
        info_file = character / "character.json"
        if info_file.exists():
            info = json.loads(info_file.read_text(encoding="utf-8"))
        else:
            info = {"character_id": character.name}
        result[character.name] = info
    return result


def save_character_profile(character_id: str, payload: Dict[str, str]) -> None:
    directory = character_dir(character_id)
    profile_path = directory / "character.json"
    profile = {"character_id": character_id, **payload, "updated_at": utc_timestamp()}
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def register_input_image(character_id: str, job_id: str, filename: str) -> Path:
    inputs_dir = character_dir(character_id) / "inputs" / job_id
    inputs_dir.mkdir(parents=True, exist_ok=True)
    return inputs_dir / filename


def latest_job(character_id: str) -> Optional[str]:
    outputs_dir = character_dir(character_id) / "outputs"
    if not outputs_dir.exists():
        return None
    jobs = sorted([path for path in outputs_dir.iterdir() if path.is_dir()])
    return jobs[-1].name if jobs else None
