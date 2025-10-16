"""Simplified pipeline that emulates DrawingSpinUp rigging output."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from PIL import Image

from .storage import job_dir, register_input_image, save_metadata, utc_timestamp


@dataclass
class PipelineResult:
    character_id: str
    job_id: str
    mesh_path: Path
    rig_path: Path
    texture_path: Path
    preview_path: Path

    def as_response(self) -> Dict[str, str]:
        return {
            "character_id": self.character_id,
            "job_id": self.job_id,
            "mesh_path": str(self.mesh_path),
            "rig_path": str(self.rig_path),
            "texture_path": str(self.texture_path),
            "preview_path": str(self.preview_path),
        }


class RiggingPipeline:
    """Placeholder pipeline that stores inputs and fabricates simple mesh outputs."""

    def run(self, character_id: str, image_path: Path) -> PipelineResult:
        job_id = uuid.uuid4().hex[:12]
        recorded_input = self._store_input_image(character_id, job_id, image_path)
        outputs = job_dir(character_id, job_id)

        mesh_path = outputs / "model.obj"
        rig_path = outputs / "rig.json"
        texture_path = outputs / "albedo.png"
        preview_path = outputs / "preview.png"

        self._generate_placeholder_mesh(mesh_path)
        self._generate_placeholder_rig(rig_path)
        self._generate_texture(recorded_input, texture_path)
        self._generate_preview(recorded_input, preview_path)

        metadata = {
            "character_id": character_id,
            "job_id": job_id,
            "created_at": utc_timestamp(),
            "artifacts": {
                "mesh": str(mesh_path),
                "rig": str(rig_path),
                "texture": str(texture_path),
                "preview": str(preview_path),
            },
        }
        save_metadata(character_id, job_id, metadata)
        return PipelineResult(character_id, job_id, mesh_path, rig_path, texture_path, preview_path)

    def _store_input_image(self, character_id: str, job_id: str, image_path: Path) -> Path:
        target = register_input_image(character_id, job_id, image_path.name)
        target.write_bytes(image_path.read_bytes())
        return target

    def _generate_placeholder_mesh(self, mesh_path: Path) -> None:
        mesh_content = """# Simple quad mesh\nmtllib none\nusemtl default\n"""
        mesh_content += "\n".join(
            [
                "v -1.0 0.0 -1.0",
                "v 1.0 0.0 -1.0",
                "v 1.0 0.0 1.0",
                "v -1.0 0.0 1.0",
                "vt 0.0 0.0",
                "vt 1.0 0.0",
                "vt 1.0 1.0",
                "vt 0.0 1.0",
                "vn 0.0 1.0 0.0",
                "f 1/1/1 2/2/1 3/3/1",
                "f 1/1/1 3/3/1 4/4/1",
            ]
        )
        mesh_path.write_text(mesh_content, encoding="utf-8")

    def _generate_placeholder_rig(self, rig_path: Path) -> None:
        rig = {
            "skeleton": [
                {"name": "root", "parent": None, "translation": [0, 0, 0]},
                {"name": "spine", "parent": "root", "translation": [0, 1, 0]},
                {"name": "head", "parent": "spine", "translation": [0, 1, 0]},
            ],
            "metadata": {"source": "placeholder"},
        }
        rig_path.write_text(json.dumps(rig, indent=2), encoding="utf-8")

    def _generate_texture(self, image_path: Path, texture_path: Path) -> None:
        image = Image.open(image_path).convert("RGB")
        image.save(texture_path)

    def _generate_preview(self, image_path: Path, preview_path: Path) -> None:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((512, 512))
        image.save(preview_path)


__all__ = ["RiggingPipeline", "PipelineResult"]
