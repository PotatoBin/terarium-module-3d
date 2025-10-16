from pathlib import Path

from PIL import Image

from server.app.pipeline import RiggingPipeline
from server.app.config import settings


def create_dummy_image(tmp_path: Path) -> Path:
    path = tmp_path / "input.png"
    image = Image.new("RGB", (128, 128), color=(255, 0, 0))
    image.save(path)
    return path


def test_pipeline_generates_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_root", tmp_path)
    pipeline = RiggingPipeline()
    image_path = create_dummy_image(tmp_path)

    result = pipeline.run("test-character", image_path)

    assert result.mesh_path.exists()
    assert result.rig_path.exists()
    assert result.texture_path.exists()
    assert result.preview_path.exists()

    metadata_path = result.mesh_path.parent / "metadata.json"
    assert metadata_path.exists()
