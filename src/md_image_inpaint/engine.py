from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from .models import ImageTask, ProgressEvent, RunConfig


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
    completed = _run_subprocess(cmd, config)
    if config.verbose and completed.stdout.strip():
        logs.append("IOPaint stdout:\n" + completed.stdout.strip())
    if completed.stderr.strip():
        logs.append("IOPaint stderr:\n" + completed.stderr.strip())
    if completed.returncode != 0:
        raise EngineError(f"IOPaint failed with exit code {completed.returncode}")

    for index, task in enumerate(processable, start=1):
        expected = _find_output_image(output_images_dir, task.batch_image_path)
        if expected is not None:
            task.output_path = expected.resolve()
            task.success = True
            logs.append(f"Processed: {task.reference.raw_path} -> {expected.name}")
            _emit_task_progress(config, processable, task, index, f"Processed image: {task.reference.raw_path}")
        else:
            task.success = False
            task.error = f"expected output image missing: {output_images_dir / task.batch_image_path.name}"
            logs.append(f"Failed: {task.reference.raw_path}; {task.error}")
            _emit_task_progress(config, processable, task, index, f"Failed image: {task.reference.raw_path}")
    return logs


def _run_subprocess(cmd: list[str], config: RunConfig) -> subprocess.CompletedProcess[str]:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    threads = [
        threading.Thread(target=_read_stream, args=(process.stdout, stdout_lines, config, "IOPaint"), daemon=True),
        threading.Thread(target=_read_stream, args=(process.stderr, stderr_lines, config, "IOPaint"), daemon=True),
    ]
    for thread in threads:
        thread.start()

    while True:
        if config.cancel_token and config.cancel_token.cancelled:
            stdout, stderr = _terminate_process(process)
            _join_threads(threads)
            if stdout:
                stdout_lines.append(stdout)
            if stderr:
                stderr_lines.append(stderr)
            raise EngineError("processing cancelled by user")
        return_code = process.poll()
        if return_code is not None:
            _join_threads(threads)
            return subprocess.CompletedProcess(cmd, return_code, "".join(stdout_lines), "".join(stderr_lines))
        time.sleep(0.2)


def _read_stream(stream, target: list[str], config: RunConfig, prefix: str) -> None:
    if stream is None:
        return
    for line in stream:
        target.append(line)
        text = line.strip()
        if text and config.progress_callback:
            config.progress_callback(ProgressEvent(stage="processing", message=f"{prefix}: {text}"))


def _emit_task_progress(config: RunConfig, processable: list[ImageTask], task: ImageTask, index: int, message: str) -> None:
    if config.progress_callback is None:
        return
    config.progress_callback(
        ProgressEvent(
            stage="processing",
            message=message,
            current=index,
            total=len(processable),
            success_count=sum(1 for item in processable if item.success),
            failed_count=sum(1 for item in processable if item.error),
        )
    )


def _join_threads(threads: list[threading.Thread]) -> None:
    for thread in threads:
        thread.join(timeout=1)


def _terminate_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, text=True, check=False)
    else:
        process.terminate()
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate()


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
