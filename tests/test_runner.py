from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image

from md_image_inpaint.models import RunConfig
from md_image_inpaint.runner import run


def test_runner_calls_iopaint_and_rewrites_successful_images(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(
        RunConfig(
            markdown_path=md_path,
            out_dir=out_dir,
            mask_dir=mask_dir,
            iopaint_cmd=str(fake_cmd),
            model_dir=tmp_path / "model-cache",
            verbose=True,
        )
    )

    assert result.failed_count == 0
    assert result.success_count == 1
    assert result.output_markdown_path is not None
    rewritten = result.output_markdown_path.read_text(encoding="utf-8")
    assert "![sample](images/0001-sample.png)" in rewritten
    assert "![remote](https://example.com/remote.png)" in rewritten
    assert "![missing](images/missing.png)" in rewritten
    assert (out_dir / "images" / "0001-sample.png").exists()
    assert (out_dir / "backups" / "original.md").exists()
    assert any("Running IOPaint" in line for line in result.logs)
    assert any("--model-dir=" in line for line in result.logs)


def test_runner_accepts_iopaint_png_output_for_jpg_input(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0, output_suffix=".png")
    md_path, mask_dir = _make_sample_doc(tmp_path, image_suffix=".jpg")
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, iopaint_cmd=str(fake_cmd)))

    assert result.failed_count == 0
    assert result.success_count == 1
    rewritten = (out_dir / "document.md").read_text(encoding="utf-8")
    assert "![sample](images/0001-sample.png)" in rewritten
    assert (out_dir / "images" / "0001-sample.png").exists()


def test_runner_dry_run_lists_work_without_writing(tmp_path: Path) -> None:
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, dry_run=True))

    assert result.output_markdown_path is None
    assert not out_dir.exists()
    assert any("Will process: images/sample.png" in line for line in result.logs)
    assert any("Dry run enabled" in line for line in result.logs)


def test_runner_keeps_original_reference_when_iopaint_fails(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=7)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(
        RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, iopaint_cmd=str(fake_cmd))
    )

    assert result.failed_count == 1
    assert result.output_markdown_path is not None
    rewritten = result.output_markdown_path.read_text(encoding="utf-8")
    assert "![sample](images/sample.png)" in rewritten
    assert any("IOPaint failure" in line for line in result.logs)
    assert any("Kept original reference" in line for line in result.logs)


def test_runner_logs_missing_mask(tmp_path: Path) -> None:
    md_path, _mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir))

    assert result.success_count == 0
    assert any("mask missing" in line for line in result.logs)
    rewritten = (out_dir / "document.md").read_text(encoding="utf-8")
    assert "![sample](images/sample.png)" in rewritten


def test_runner_applies_config_skip_patterns(tmp_path: Path) -> None:
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(
        RunConfig(
            markdown_path=md_path,
            out_dir=out_dir,
            mask_dir=mask_dir,
            skip_patterns=["images/*.png"],
            dry_run=True,
        )
    )

    assert result.success_count == 0
    assert any("Will skip: images/sample.png; matched skip pattern: images/*.png" in line for line in result.logs)


def _make_sample_doc(tmp_path: Path, image_suffix: str = ".png") -> tuple[Path, Path]:
    image_dir = tmp_path / "images"
    mask_dir = tmp_path / "masks"
    image_dir.mkdir()
    mask_dir.mkdir()
    image_name = f"sample{image_suffix}"
    Image.new("RGB", (6, 6), "blue").save(image_dir / image_name)
    Image.new("L", (6, 6), 255).save(mask_dir / image_name)
    md_path = tmp_path / "document.md"
    md_path.write_text(
        "\n".join(
            [
                "# Demo",
                f"![sample](images/{image_name})",
                "![remote](https://example.com/remote.png)",
                "![missing](images/missing.png)",
            ]
        ),
        encoding="utf-8",
    )
    return md_path, mask_dir


def _make_fake_iopaint(tmp_path: Path, exit_code: int, output_suffix: str | None = None) -> Path:
    script = tmp_path / "fake_iopaint.py"
    script_text = """
from pathlib import Path
import shutil
import sys

if not any(arg == "run" for arg in sys.argv):
    sys.exit(3)

args = {}
for arg in sys.argv:
    if arg.startswith("--") and "=" in arg:
        key, value = arg[2:].split("=", 1)
        args[key] = value

if __EXIT_CODE__ != 0:
    print("fake failure", file=sys.stderr)
    sys.exit(__EXIT_CODE__)

image_dir = Path(args["image"])
output_dir = Path(args["output"])
output_dir.mkdir(parents=True, exist_ok=True)
for image in image_dir.iterdir():
    output_name = image.name
    if __OUTPUT_SUFFIX__ is not None:
        output_name = image.with_suffix(__OUTPUT_SUFFIX__).name
    shutil.copy2(image, output_dir / output_name)
"""
    script.write_text(
        script_text.replace("__EXIT_CODE__", str(exit_code)).replace("__OUTPUT_SUFFIX__", repr(output_suffix)),
        encoding="utf-8",
    )
    cmd = tmp_path / "iopaint.cmd"
    cmd.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    return cmd
