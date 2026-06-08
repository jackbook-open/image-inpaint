from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw


SUPPORTED_MASK_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
REGIONS = ("none", "top-left", "top-right", "bottom-left", "bottom-right", "bottom-strip")


def find_matching_mask(image_path: Path, mask_dir: Path | None) -> Path | None:
    if mask_dir is None or not mask_dir.exists():
        return None
    exact = mask_dir / image_path.name
    if exact.exists():
        return exact.resolve()
    for suffix in SUPPORTED_MASK_SUFFIXES:
        candidate = mask_dir / f"{image_path.stem}{suffix}"
        if candidate.exists():
            return candidate.resolve()
    return None


def create_region_mask(image_path: Path, region: str | None, output_dir: Path) -> Path | None:
    if region is None or region == "none":
        return None
    if region not in REGIONS:
        raise ValueError(f"unsupported region: {region}")

    with Image.open(image_path) as image:
        width, height = image.size

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    box = _region_box(width, height, region)
    draw.rectangle(box, fill=255)

    output_dir.mkdir(parents=True, exist_ok=True)
    mask_path = output_dir / f"{image_path.stem}-{region}-{uuid4().hex[:8]}.png"
    mask.save(mask_path)
    return mask_path


def _region_box(width: int, height: int, region: str) -> tuple[int, int, int, int]:
    block_w = max(1, width // 4)
    block_h = max(1, height // 4)
    if region == "top-left":
        return (0, 0, block_w, block_h)
    if region == "top-right":
        return (width - block_w, 0, width, block_h)
    if region == "bottom-left":
        return (0, height - block_h, block_w, height)
    if region == "bottom-right":
        return (width - block_w, height - block_h, width, height)
    if region == "bottom-strip":
        strip_h = max(1, height // 5)
        return (0, height - strip_h, width, height)
    raise ValueError(f"unsupported region: {region}")
