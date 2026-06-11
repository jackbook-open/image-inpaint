from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

from PIL import Image

from md_image_inpaint.models import CancelToken, ProgressEvent, RunConfig
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

    assert result.dry_run is False
    assert result.failed_count == 0
    assert result.success_count == 1
    assert result.output_markdown_path is not None
    rewritten = result.output_markdown_path.read_text(encoding="utf-8")
    assert "![sample](images/0001-sample.png)" in rewritten
    assert "![remote](https://example.com/remote.png)" in rewritten
    assert "![missing](images/missing.png)" in rewritten
    assert (out_dir / "images" / "0001-sample.png").exists()
    assert (out_dir / "backups" / "original.md").exists()
    assert result.log_path == out_dir / "logs" / "run.log"
    assert result.log_path.exists()
    assert "Summary: processed=1, skipped=2, failed=0" in result.log_path.read_text(encoding="utf-8")
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


def test_runner_uses_new_output_directory_when_requested_one_has_files(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    existing = out_dir / "document.md"
    existing.write_text("keep me", encoding="utf-8")

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, iopaint_cmd=str(fake_cmd)))

    assert existing.read_text(encoding="utf-8") == "keep me"
    assert result.output_markdown_path == tmp_path / "output-1" / "document.md"
    assert result.output_markdown_path.exists()
    assert any(f"Output folder: {tmp_path / 'output-1'}" in line for line in result.logs)


def test_runner_can_use_empty_existing_output_directory(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, iopaint_cmd=str(fake_cmd)))

    assert result.output_markdown_path == out_dir / "document.md"
    assert result.output_markdown_path.exists()


def test_runner_dry_run_lists_work_without_writing(tmp_path: Path) -> None:
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"
    events: list[ProgressEvent] = []

    result = run(
        RunConfig(
            markdown_path=md_path,
            out_dir=out_dir,
            mask_dir=mask_dir,
            dry_run=True,
            progress_callback=events.append,
        )
    )

    assert result.dry_run is True
    assert result.output_markdown_path is None
    assert not out_dir.exists()
    assert any("Will process: images/sample.png" in line for line in result.logs)
    assert any("Ready: images/sample.png; mask=" in line for line in result.logs)
    assert any("Dry run enabled" in line for line in result.logs)
    assert [event.stage for event in events] == ["scan", "masks", "complete"]
    assert events[-1].total == 3
    assert events[-1].skipped_count == 2


def test_runner_dry_run_reports_missing_mask_without_writing(tmp_path: Path) -> None:
    md_path, _mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, dry_run=True))

    assert result.output_markdown_path is None
    assert not out_dir.exists()
    assert result.skipped_count == 3
    assert any("mask missing" in line for line in result.logs)


def test_runner_dry_run_reports_generated_region_mask_without_writing(tmp_path: Path) -> None:
    md_path, _mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, region="bottom-right", dry_run=True))

    assert result.output_markdown_path is None
    assert not out_dir.exists()
    assert result.skipped_count == 2
    assert result.tasks[0].should_process is True
    assert result.tasks[0].mask_path is None
    assert "fallback area will generate mask: bottom-right" in result.tasks[0].reason
    assert any("fallback area will generate mask=bottom-right" in line for line in result.logs)


def test_runner_dry_run_reports_mismatched_mask_size(tmp_path: Path) -> None:
    md_path, mask_dir = _make_sample_doc(tmp_path)
    Image.new("L", (3, 3), 255).save(mask_dir / "sample.png")
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir, dry_run=True))

    assert result.output_markdown_path is None
    assert not out_dir.exists()
    assert result.skipped_count == 3
    assert any("mask size does not match image" in line for line in result.logs)


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


def test_runner_skips_mismatched_mask_size(tmp_path: Path) -> None:
    md_path, mask_dir = _make_sample_doc(tmp_path)
    Image.new("L", (3, 3), 255).save(mask_dir / "sample.png")
    out_dir = tmp_path / "output"

    result = run(RunConfig(markdown_path=md_path, out_dir=out_dir, mask_dir=mask_dir))

    assert result.success_count == 0
    assert result.skipped_count == 3
    assert any("mask size does not match image" in line for line in result.logs)
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


def test_runner_cancels_long_iopaint_process(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0, sleep_seconds=10)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    out_dir = tmp_path / "output"
    token = CancelToken()
    result: dict[str, object] = {}

    def worker() -> None:
        result["run"] = run(
            RunConfig(
                markdown_path=md_path,
                out_dir=out_dir,
                mask_dir=mask_dir,
                iopaint_cmd=str(fake_cmd),
                cancel_token=token,
            )
        )

    thread = threading.Thread(target=worker)
    thread.start()
    time.sleep(0.5)
    token.cancel()
    thread.join(timeout=8)

    assert not thread.is_alive()
    run_result = result["run"]
    assert run_result.failed_count == 1
    assert not (out_dir / "document.md").exists()
    assert any(task.error == "processing cancelled by user" for task in run_result.tasks)


def test_runner_emits_progress_for_real_run(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0)
    md_path, mask_dir = _make_sample_doc(tmp_path)
    events: list[ProgressEvent] = []

    result = run(
        RunConfig(
            markdown_path=md_path,
            out_dir=tmp_path / "output",
            mask_dir=mask_dir,
            iopaint_cmd=str(fake_cmd),
            progress_callback=events.append,
        )
    )

    assert result.success_count == 1
    stages = [event.stage for event in events]
    assert stages[0:3] == ["scan", "backup", "masks"]
    assert stages[-2:] == ["writing", "complete"]
    messages = [event.message for event in events]
    assert "Preparing image: images/sample.png" in messages
    assert "Processed image: images/sample.png" in messages
    assert events[-1].success_count == 1
    assert events[-1].skipped_count == 2
    assert events[-1].failed_count == 0


def test_runner_streams_iopaint_output_as_progress(tmp_path: Path) -> None:
    fake_cmd = _make_fake_iopaint(tmp_path, exit_code=0, stdout_lines=["Downloading model", "Painting image"])
    md_path, mask_dir = _make_sample_doc(tmp_path)
    events: list[ProgressEvent] = []

    result = run(
        RunConfig(
            markdown_path=md_path,
            out_dir=tmp_path / "output",
            mask_dir=mask_dir,
            iopaint_cmd=str(fake_cmd),
            verbose=True,
            progress_callback=events.append,
        )
    )

    messages = [event.message for event in events]
    assert result.success_count == 1
    assert any("IOPaint: Downloading model" in message for message in messages)
    assert any("IOPaint stdout:" in line and "Painting image" in line for line in result.logs)


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


def _make_fake_iopaint(
    tmp_path: Path,
    exit_code: int,
    output_suffix: str | None = None,
    sleep_seconds: int = 0,
    stdout_lines: list[str] | None = None,
) -> Path:
    script = tmp_path / "fake_iopaint.py"
    script_text = """
from pathlib import Path
import shutil
import sys
import time

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

if __SLEEP_SECONDS__:
    time.sleep(__SLEEP_SECONDS__)

for line in __STDOUT_LINES__:
    print(line, flush=True)

image_dir = Path(args["image"])
output_dir = Path(args["output"])
output_dir.mkdir(parents=True, exist_ok=True)
for image in image_dir.iterdir():
    output_name = image.name
    if __OUTPUT_SUFFIX__ is not None:
        output_name = image.with_suffix(__OUTPUT_SUFFIX__).name
    shutil.copy2(image, output_dir / output_name)
"""
    rendered_script = (
        script_text.replace("__EXIT_CODE__", str(exit_code))
        .replace("__OUTPUT_SUFFIX__", repr(output_suffix))
        .replace("__SLEEP_SECONDS__", str(sleep_seconds))
        .replace("__STDOUT_LINES__", repr(stdout_lines or []))
    )
    script.write_text(rendered_script, encoding="utf-8")
    cmd = tmp_path / "iopaint.cmd"
    cmd.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    return cmd
