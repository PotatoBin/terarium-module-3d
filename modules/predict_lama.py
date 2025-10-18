# lama_runner/predict_lama.py
from __future__ import annotations

import os
from pathlib import Path
import cv2
import numpy as np
import torch
import yaml
from omegaconf import OmegaConf
from torch.utils.data._utils.collate import default_collate
import tqdm

from saicinpainting.training.data.datasets import make_default_val_dataset
from saicinpainting.training.modules import make_generator


def _load_checkpoint(config, ckpt_path, map_location="cpu", strict=False):
    model = make_generator(**config.generator)
    state = torch.load(ckpt_path, map_location=map_location)
    model.load_state_dict(state, strict=strict)
    model.eval()
    return model


def _move_to_device(obj, device):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, torch.nn.Module):
        return obj.to(device)
    if torch.is_tensor(obj):
        return obj.to(device)
    if isinstance(obj, (tuple, list)):
        return [_move_to_device(el, device) for el in obj]
    if isinstance(obj, dict):
        return {k: _move_to_device(v, device) for k, v in obj.items()}
    return obj


def run_lama_for_uid(
    config_path: str,
    indir: str | os.PathLike,
    uid: str,
    save_name_override: str | None = None,
) -> Path:
    """
    단일 uid(=sha256 디렉토리)만 처리.
    indir/uid/char/input.png 를 읽고, char/<save_name>_inpainted.png 로 저장.
    """
    indir = Path(indir)
    uid_dir = indir / uid
    char_dir = uid_dir / "char"
    input_png = char_dir / "input.png"
    assert input_png.exists(), f"input not found: {input_png}"

    with open(config_path, "r") as f:
        predict_config = OmegaConf.create(yaml.safe_load(f))

    # 동적으로 경로/파라미터 보정
    predict_config.indir = str(indir)           # 데이터 루트
    predict_config.uid_json = None              # 우리는 dataset이 uid 폴더 스캔하도록 설정할 것
    predict_config.dataset.indir = str(indir)   # 일부 dataset 구현은 이 키를 씀
    predict_config.dataset.specific_uid = uid   # 커스텀 키(우리가 쓸 것)

    device = torch.device(predict_config.device)
    ckpt_path = Path(predict_config.pretrained.path) / "models" / predict_config.pretrained.generator_checkpoint
    model = _load_checkpoint(predict_config, ckpt_path, map_location="cpu", strict=False).to(device)

    # ----- dataset 구성 -----
    # LaMa의 make_default_val_dataset 은 보통 디렉토리 구조/옵션을 요구한다.
    # 여기서는 "characters/<uid>/char/input.png" 만 처리하도록 작은 헬퍼 dataset을 만든다.
    dataset = _OneImageDataset(str(input_png))

    # ----- 추론 -----
    for img_i in tqdm.trange(len(dataset), desc=f"LaMa[{uid}]"):
        batch = default_collate([dataset[img_i]])
        with torch.no_grad():
            batch = _move_to_device(batch, device)
            # LaMa generator 는 (B, C, H, W) float32 [-1, 1] or [0,1] 를 기대.
            # 여기선 간단화를 위해 [0,1] RGB, 별도 마스크 합성 후 OpenCV 인페인팅을 적용.
            # (네가 준 코드처럼 모델 출력으로 마스크 예측 -> inpaint)
            predicted = model(batch["input"])  # (B,1,H,W) 과 유사한 바이너리 맵이라 가정
            batch["predicted"] = predicted

        # 복원/후처리
        _save_inpainted(batch, char_dir, save_name_override or predict_config.generator.kind)

    return char_dir / f"{save_name_override or predict_config.generator.kind}_inpainted.png"


class _OneImageDataset:
    """
    characters/<uid>/char/input.png 하나만 쓰는 극단적 검증 dataset.
    - 반환: dict with "input": (C,H,W) torch.float32 [0,1]
            "uid":  [uid-like string]
    """
    def __init__(self, img_path: str):
        import torch
        self.img_path = img_path
        self.uid = Path(img_path).parent.parent.name  # <uid>
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(img_path)

        # RGBA or RGB → RGB+alpha 분리
        if img.shape[2] == 4:
            bgr = img[:, :, :3]
            alpha = img[:, :, 3]
        else:
            bgr = img
            alpha = np.full(bgr.shape[:2], 255, dtype=np.uint8)

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        a = (alpha.astype(np.float32) / 255.0)[..., None]  # (H,W,1)
        inp = np.concatenate([rgb, a], axis=2)            # (H,W,4)

        self.tensor = torch.from_numpy(inp).permute(2, 0, 1)  # (4,H,W)

    def __len__(self):
        return 1

    def __getitem__(self, idx):
        return {"input": self.tensor, "uid": self.uid}


def _save_inpainted(batch, char_dir: Path, save_name: str):
    """
    batch['input']: (B,4,H,W) RGB+A
    batch['predicted']: (B,1,H,W) ~ contour mask logits 라고 가정
    → predicted > 0.2 를 마스크로 만들고, alpha 빈 곳과 합쳐 inpaint
    """
    import torch

    x = batch["input"][0].detach().cpu().permute(1, 2, 0).numpy()  # (H,W,4)
    img = (x[:, :, 0:3] * 255).astype("uint8")
    alpha = (x[:, :, 3:4] * 255).astype("uint8")

    pred = batch["predicted"][0][0].detach().cpu().numpy()
    pred = np.clip((pred > 0.2) * 255, 0, 255).astype("uint8")

    inpaint_mask = np.maximum(pred, 255 - alpha[:, :, 0]).astype(np.uint8)
    inpainted = cv2.inpaint(img, inpaint_mask, 3, cv2.INPAINT_TELEA)
    out = np.concatenate([inpainted, alpha], 2)  # (H,W,4)

    char_dir.mkdir(parents=True, exist_ok=True)
    out_path = char_dir / f"{save_name}_inpainted.png"
    cv2.imwrite(str(out_path), cv2.cvtColor(out, cv2.COLOR_BGRA2RGBA))
