from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import ImageTask, RunConfig


class EngineError(RuntimeError):
    pass


IOPAINT_OUTPUT_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def run_engine(config: RunConfig, tasks: list[ImageTask], batch_image_dir: Path, batch_mask_dir: Path, output_images_dir: Path) -> list[str]:
    logs: list[str] = []
    processable = [task for task in tasks if task.should_process and task.batch_image_path and task.batch_mask_path]
    if not processable:
        logs.append("No processable local images with masks were found.")
        return logs

    if config.engine != "iopaint":
        raise EngineError(f"unsupported engine: {config.engine}")

    cmd = [
        config.iopaint_cmd,
        "run",
        f"--model={config.model}",
        f"--device={config.device}",
        f"--image={batch_image_dir}",
        f"--mask={batch_mask_dir}",
        f"--output={output_images_dir}",
    ]
    if config.model_dir is not None:
        config.model_dir.mkdir(parents=True, exist_ok=True)
        cmd.append(f"--model-dir={config.model_dir}")
    logs.append("Running IOPaint: " + " ".join(str(part) for part in cmd))
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if config.verbose and completed.stdout.strip():
        logs.append("IOPaint stdout:\n" + completed.stdout.strip())
    if completed.stderr.strip():
        logs.append("IOPaint stderr:\n" + completed.stderr.strip())
    if completed.returncode != 0:
        raise EngineError(f"IOPaint failed with exit code {completed.returncode}")

    for task in processable:
        expected = _find_output_image(output_images_dir, task.batch_image_path)
        if expected is not None:
            task.output_path = expected.resolve()
            task.success = True
            logs.append(f"Processed: {task.reference.raw_path} -> {expected.name}")
        else:
            task.success = False
            task.error = f"expected output image missing: {output_images_dir / task.batch_image_path.name}"
            logs.append(f"Failed: {task.reference.raw_path}; {task.error}")
    return logs


def _find_output_image(output_images_dir: Path, batch_image_path: Path) -> Path | None:
    exact = output_images_dir / batch_image_path.name
    if exact.exists():
        return exact

    for suffix in IOPAINT_OUTPUT_SUFFIXES:
        candidate = output_images_dir / f"{batch_image_path.stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def copy_original_to_output(task: ImageTask, output_images_dir: Path) -> None:
    if task.reference.resolved_path is None:
        return
    output_images_dir.mkdir(parents=True, exist_ok=True)
    target = output_images_dir / task.reference.resolved_path.name
    shutil.copy2(task.reference.resolved_path, target)
    task.output_path = target.resolve()
    task.success = True
