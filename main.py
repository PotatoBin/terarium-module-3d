# main.py (일부 발췌) — /characters 엔드포인트 교체

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Optional
import imghdr

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# === 추가: PIL, 라마 러너 ===
from PIL import Image
from modules.predict_lama import run_lama_for_uid

# ===== 설정 =====
BASE_DIR = Path(__file__).resolve().parent
STORE_DIR = BASE_DIR / "characters"
STORE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_PREFIX = "image/"
IMGHDR_TO_EXT = {
    "jpeg": "jpg",
    "png": "png",
    "gif": "gif",
    "bmp": "bmp",
    "tiff": "tif",
    "rgb": "rgb",
    "pbm": "pbm",
    "pgm": "pgm",
    "ppm": "ppm",
    "xbm": "xbm",
}

app = FastAPI(title="Characters Uploader", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


def _detect_ext(data: bytes, content_type: Optional[str]) -> str:
    kind = imghdr.what(None, data)
    if kind:
        return IMGHDR_TO_EXT.get(kind, kind)
    if content_type:
        if content_type.endswith("/png"):
            return "png"
        if content_type.endswith("/jpeg") or content_type.endswith("/jpg"):
            return "jpg"
        if content_type.endswith("/webp"):
            return "webp"
        if content_type.endswith("/gif"):
            return "gif"
    return "png"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ensure_png_for_lama(src_path: Path, dst_png: Path) -> None:
    """라마 입력용 RGBA PNG로 통일."""
    dst_png.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as im:
        # RGBA로 맞추고 저장
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        im.save(dst_png, format="PNG")


@app.post("/characters")
async def upload_character_image(file: UploadFile = File(...)):
    # 1) MIME 1차 체크
    if not file.content_type or not file.content_type.startswith(ALLOWED_MIME_PREFIX):
        raise HTTPException(status_code=415, detail="only image/* accepted")

    # 2) 내용 읽기 & 2차 포맷 감지
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    ext = _detect_ext(data, file.content_type)

    # 3) 해시 디렉토리 생성
    h = _hash_bytes(data)
    dest_dir = STORE_DIR / h
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 4) 원본 저장 (input.<ext>)
    orig_path = dest_dir / f"input.{ext}"
    orig_path.write_bytes(data)

    # 5) 라마 입력 PNG 준비: characters/<h>/char/input.png
    char_dir = dest_dir / "char"
    lama_input_png = char_dir / "input.png"
    try:
        _ensure_png_for_lama(orig_path, lama_input_png)
    except Exception as e:
        (dest_dir / "logs.txt").write_text(f"[PNG-CONVERT] {e}\n", encoding="utf-8")

    # 6) 라마 실행 (실패해도 API는 ok)
    try:
        cfg_path = BASE_DIR / "lama_runner" / "configs" / "prediction" / "lama-fourier.yaml"
        run_lama_for_uid(
            config_path=str(cfg_path),
            indir=str(STORE_DIR),  # characters 루트
            uid=h,
        )
    except Exception as e:
        # 요구사항상 응답은 status만이므로, 실패는 로그에만 기록
        with open(dest_dir / "logs.txt", "a", encoding="utf-8") as fp:
            fp.write(f"[LaMa] {e}\n")

    # 7) 상태만 반환
    return JSONResponse({"status": "ok"})
