from pathlib import Path

from PIL import Image

from md_image_inpaint.masks import create_region_mask, find_matching_mask


def test_find_matching_mask_prefers_exact_filename(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    mask_dir = tmp_path / "masks"
    mask_dir.mkdir()
    exact = mask_dir / "image.png"
    alternate = mask_dir / "image.jpg"
    image.write_bytes(b"image")
    exact.write_bytes(b"exact")
    alternate.write_bytes(b"alternate")

    assert find_matching_mask(image, mask_dir) == exact.resolve()


def test_create_bottom_right_region_mask(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    Image.new("RGB", (8, 8), "blue").save(image)

    mask_path = create_region_mask(image, "bottom-right", tmp_path / "generated")

    assert mask_path is not None
    with Image.open(mask_path) as mask:
        assert mask.size == (8, 8)
        assert mask.getpixel((0, 0)) == 0
        assert mask.getpixel((7, 7)) == 255


def test_create_bottom_strip_region_mask(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    Image.new("RGB", (10, 10), "blue").save(image)

    mask_path = create_region_mask(image, "bottom-strip", tmp_path / "generated")

    assert mask_path is not None
    with Image.open(mask_path) as mask:
        assert mask.getpixel((5, 0)) == 0
        assert mask.getpixel((5, 9)) == 255
