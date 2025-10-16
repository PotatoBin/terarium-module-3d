"""FastAPI application exposing the rigging pipeline."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .gpu_pool import GpuPool
from .pipeline import RiggingPipeline
from .schemas import CharacterCreate, CharacterResponse, JobResponse
from .storage import (
    character_dir,
    list_characters,
    save_character_profile,
    utc_timestamp,
    latest_job,
)


def create_app() -> FastAPI:
    app = FastAPI(title="DrawingSpinUp Rigging Service", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    gpu_pool = GpuPool(settings.gpu_ids, max_slots=settings.max_concurrent_jobs)
    pipeline = RiggingPipeline()

    @app.on_event("startup")
    async def ensure_directories() -> None:
        settings.data_root.mkdir(parents=True, exist_ok=True)

    @app.get("/healthz")
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok", "timestamp": utc_timestamp()}

    @app.post("/characters", response_model=CharacterResponse)
    async def create_character(payload: CharacterCreate) -> CharacterResponse:
        character_id = payload.name.lower().replace(" ", "-")
        save_character_profile(character_id, payload.dict())
        character_dir(character_id)
        return CharacterResponse(
            character_id=character_id,
            name=payload.name,
            description=payload.description,
            updated_at=utc_timestamp(),
            latest_job=None,
            metadata={}
        )

    @app.get("/characters", response_model=Dict[str, CharacterResponse])
    async def get_characters() -> Dict[str, CharacterResponse]:
        response: Dict[str, CharacterResponse] = {}
        for character_id, info in list_characters().items():
            response[character_id] = CharacterResponse(
                character_id=character_id,
                name=info.get("name"),
                description=info.get("description"),
                updated_at=info.get("updated_at"),
                latest_job=latest_job(character_id),
                metadata={k: str(v) for k, v in info.items() if k not in {"name", "description", "updated_at", "character_id"}},
            )
        return response

    async def run_job(character_id: str, image_file: UploadFile) -> JobResponse:
        tmp_name = f"{character_id}-{uuid.uuid4().hex}{Path(image_file.filename).suffix}" if image_file.filename else f"{character_id}-{uuid.uuid4().hex}.png"
        temp_path = settings.data_root / "tmp" / tmp_name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        contents = await image_file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="빈 파일은 처리할 수 없습니다.")
        temp_path.write_bytes(contents)

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, pipeline.run, character_id, temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
        return JobResponse(**result.as_response())

    @app.post("/characters/{character_id}/jobs", response_model=JobResponse)
    async def submit_job(
        character_id: str,
        file: UploadFile = File(...),
    ) -> JobResponse:
        available_characters = list_characters()
        if character_id not in available_characters:
            raise HTTPException(status_code=404, detail="캐릭터를 찾을 수 없습니다.")

        with gpu_pool.reserve() as gpu_id:
            # GPU id can be used for logging or future expansion.
            print(f"[job] character={character_id} assigned_gpu={gpu_id}")
            return await run_job(character_id, file)

    return app


app = create_app()
