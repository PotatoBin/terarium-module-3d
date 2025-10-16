"""Download assets listed in DrawingSpinUp/assets_manifest.yaml."""
from __future__ import annotations

import hashlib
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "DrawingSpinUp" / "assets_manifest.yaml"


@dataclass
class Asset:
    name: str
    url: str
    sha256: str
    destination: Path

    @classmethod
    def from_dict(cls, data: dict, base_dir: Path) -> "Asset":
        try:
            name = data["name"]
            url = data["url"]
            sha256 = data["sha256"]
            destination = base_dir / data["destination"]
        except KeyError as exc:  # pragma: no cover - defensive programming
            raise ValueError(f"Missing required key in manifest entry: {exc}") from exc
        return cls(name=name, url=url, sha256=sha256, destination=destination)


class DownloadError(RuntimeError):
    """Raised when an asset download fails."""


def iter_assets() -> Iterable[Asset]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "DrawingSpinUp/assets_manifest.yaml 파일을 찾을 수 없습니다. "
            "README.md의 지침을 참고하여 파일을 준비하세요."
        )

    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    assets = manifest.get("assets", [])
    for entry in assets:
        yield Asset.from_dict(entry, MANIFEST_PATH.parent)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as response:
        if response.status_code != 200:
            raise DownloadError(f"다운로드 실패: {url} (status={response.status_code})")
        ensure_parent_dir(destination)
        with destination.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_if_needed(asset: Asset) -> None:
    if asset.destination.suffixes[-2:] == [".tar", ".gz"]:
        extract_dir = asset.destination.with_suffix("")
        with tarfile.open(asset.destination, "r:gz") as tar:
            tar.extractall(path=extract_dir)


def main() -> None:
    if not MANIFEST_PATH.exists():
        print("Manifest not found; skipping downloads.")
        return

    downloaded_any = False
    for asset in iter_assets():
        destination = asset.destination
        if destination.exists():
            actual_hash = sha256sum(destination)
            if actual_hash == asset.sha256:
                print(f"[skip] {asset.name} (already present)")
                continue
            print(
                f"[warn] {asset.name} 해시가 일치하지 않습니다. 기존 파일을 다시 다운로드합니다."
            )

        print(f"[download] {asset.name} ← {asset.url}")
        try:
            download(asset.url, destination)
        except DownloadError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        actual_hash = sha256sum(destination)
        if asset.sha256 and actual_hash != asset.sha256:
            print(
                f"[error] {asset.name} 해시가 일치하지 않습니다. "
                f"expected={asset.sha256} actual={actual_hash}",
                file=sys.stderr,
            )
            destination.unlink(missing_ok=True)
            sys.exit(1)
        extract_if_needed(asset)
        downloaded_any = True

    if not downloaded_any:
        print("Manifest에 다운로드할 항목이 정의되어 있지 않습니다. README.md를 확인하세요.")


if __name__ == "__main__":
    main()
