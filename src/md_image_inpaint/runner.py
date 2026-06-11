from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .engine import EngineError, run_engine
from .markdown import build_tasks, rewrite_markdown
from .masks import create_region_mask, find_matching_mask, mask_size_matches
from .models import ImageTask, ProgressEvent, RunConfig, RunResult, matches_skip_pattern


def run(config: RunConfig) -> RunResult:
    _raise_if_cancelled(config)
    markdown_path = config.markdown_path.resolve()
    markdown_text = markdown_path.read_text(encoding="utf-8")
    out_dir = config.out_dir.resolve()
    output_images_dir = out_dir / "images"

    tasks = build_tasks(markdown_text, markdown_path)
    _apply_skip_patterns(tasks, config.skip_patterns)
    logs: list[str] = [f"Scanning Markdown: {markdown_path}"]
    logs.extend(_planning_logs(tasks))
    _emit_progress(config, "scan", f"Found {len(tasks)} image reference(s).", tasks)

    if config.dry_run:
        processable = _attach_masks(tasks, config, out_dir / "generated_masks", logs, dry_run=True)
        _emit_progress(config, "masks", f"Pre-check found {len(processable)} image(s) ready for processing.", tasks)
        _emit_progress(config, "complete", "Pre-check complete.", tasks)
        return RunResult(
            markdown_path=markdown_path,
            output_markdown_path=None,
            output_images_dir=output_images_dir,
            tasks=tasks,
            logs=logs + ["Dry run enabled; no files were written."],
            skipped_count=sum(1 for task in tasks if not task.should_process),
            failed_count=sum(1 for task in tasks if task.should_process and task.error),
            dry_run=True,
        )

    out_dir = _next_available_output_dir(out_dir)
    output_images_dir = out_dir / "images"
    output_markdown_path = out_dir / "document.md"
    logs.append(f"Output folder: {out_dir}")
    _prepare_output_dirs(out_dir)
    _backup_sources(markdown_path, tasks, out_dir, logs)
    _emit_progress(config, "backup", "Backed up source files.", tasks)
    if _is_cancelled(config):
        return _cancelled_result(config, markdown_path, out_dir, output_images_dir, tasks, logs)

    generated_mask_dir = out_dir / "generated_masks"
    processable = _attach_masks(tasks, config, generated_mask_dir, logs)
    _emit_progress(config, "masks", f"Prepared {len(processable)} image(s) for processing.", tasks)
    if _is_cancelled(config):
        return _cancelled_result(config, markdown_path, out_dir, output_images_dir, tasks, logs)

    if processable:
        _emit_progress(config, "processing", "Processing images...", tasks)
        with tempfile.TemporaryDirectory(prefix="md-image-inpaint-") as tmp:
            tmp_dir = Path(tmp)
            batch_image_dir = tmp_dir / "images"
            batch_mask_dir = tmp_dir / "masks"
            batch_image_dir.mkdir()
            batch_mask_dir.mkdir()
            _prepare_batch_files(processable, batch_image_dir, batch_mask_dir, config)
            try:
                logs.extend(run_engine(config, tasks, batch_image_dir, batch_mask_dir, output_images_dir))
            except EngineError as exc:
                logs.append(f"IOPaint failure: {exc}")
                for task in processable:
                    task.success = False
                    task.error = str(exc)
                    logs.append(f"Kept original reference: {task.reference.raw_path}")
    else:
        logs.append("No images were sent to IOPaint.")

    if _is_cancelled(config):
        return _cancelled_result(config, markdown_path, out_dir, output_images_dir, tasks, logs)
    _emit_progress(config, "writing", "Writing result document.", tasks)
    rewritten = rewrite_markdown(markdown_text, tasks, out_dir)
    output_markdown_path.write_text(rewritten, encoding="utf-8")
    logs.append(f"Wrote Markdown: {output_markdown_path}")

    success_count = sum(1 for task in tasks if task.success)
    failed_count = sum(1 for task in tasks if task.should_process and not task.success)
    skipped_count = sum(1 for task in tasks if not task.should_process)
    log_path = _write_run_log(out_dir, logs, success_count, skipped_count, failed_count)
    _emit_progress(config, "complete", "Processing complete.", tasks)
    return RunResult(
        markdown_path=markdown_path,
        output_markdown_path=output_markdown_path,
        output_images_dir=output_images_dir,
        log_path=log_path,
        tasks=tasks,
        logs=logs,
        success_count=success_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
    )


def _raise_if_cancelled(config: RunConfig) -> None:
    if _is_cancelled(config):
        raise EngineError("processing cancelled by user")


def _is_cancelled(config: RunConfig) -> bool:
    return bool(config.cancel_token and config.cancel_token.cancelled)


def _cancelled_result(
    config: RunConfig,
    markdown_path: Path,
    out_dir: Path,
    output_images_dir: Path,
    tasks: list[ImageTask],
    logs: list[str],
) -> RunResult:
    for task in tasks:
        if task.should_process and not task.success:
            task.error = task.error or "processing cancelled by user"
    logs.append("Processing cancelled by user; no result Markdown was written.")
    success_count = sum(1 for task in tasks if task.success)
    failed_count = sum(1 for task in tasks if task.should_process and not task.success)
    skipped_count = sum(1 for task in tasks if not task.should_process)
    log_path = _write_run_log(out_dir, logs, success_count, skipped_count, failed_count)
    _emit_progress(config, "cancelled", "Processing cancelled.", tasks)
    return RunResult(
        markdown_path=markdown_path,
        output_markdown_path=None,
        output_images_dir=output_images_dir,
        log_path=log_path,
        tasks=tasks,
        logs=logs,
        success_count=success_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
    )


def _prepare_output_dirs(out_dir: Path) -> None:
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "backups" / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)


def _next_available_output_dir(out_dir: Path) -> Path:
    if not out_dir.exists():
        return out_dir
    try:
        if out_dir.is_dir() and not any(out_dir.iterdir()):
            return out_dir
    except OSError:
        pass

    parent = out_dir.parent
    stem = out_dir.name
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}"
        if not candidate.exists():
            return candidate
        if candidate.is_dir():
            try:
                if not any(candidate.iterdir()):
                    return candidate
            except OSError:
                pass
        counter += 1


def _write_run_log(out_dir: Path, logs: list[str], success_count: int, skipped_count: int, failed_count: int) -> Path:
    log_path = out_dir / "logs" / "run.log"
    summary = f"Summary: processed={success_count}, skipped={skipped_count}, failed={failed_count}"
    log_path.write_text("\n".join([*logs, summary, ""]) , encoding="utf-8")
    logs.append(f"Wrote log: {log_path}")
    return log_path


def _apply_skip_patterns(tasks: list[ImageTask], patterns: list[str]) -> None:
    if not patterns:
        return
    for task in tasks:
        if not task.should_process:
            continue
        matched = matches_skip_pattern(task.reference.raw_path, patterns)
        if matched is None:
            continue
        task.should_process = False
        task.reason = f"matched skip pattern: {matched}"


def _backup_sources(markdown_path: Path, tasks: list[ImageTask], out_dir: Path, logs: list[str]) -> None:
    backup_md = out_dir / "backups" / "original.md"
    shutil.copy2(markdown_path, backup_md)
    logs.append(f"Backed up Markdown: {backup_md}")

    backup_image_dir = out_dir / "backups" / "images"
    seen: set[Path] = set()
    for task in tasks:
        image_path = task.reference.resolved_path
        if image_path is None or not image_path.exists() or image_path in seen:
            continue
        backup_path = backup_image_dir / _unique_name(backup_image_dir, image_path.name)
        shutil.copy2(image_path, backup_path)
        task.backup_path = backup_path.resolve()
        seen.add(image_path)
    if seen:
        logs.append(f"Backed up {len(seen)} local image(s): {backup_image_dir}")


def _attach_masks(
    tasks: list[ImageTask],
    config: RunConfig,
    generated_mask_dir: Path,
    logs: list[str],
    dry_run: bool = False,
) -> list[ImageTask]:
    processable: list[ImageTask] = []
    for task in tasks:
        if not task.should_process:
            logs.append(f"Skipped: {task.reference.raw_path}; {task.reason}")
            continue
        image_path = task.reference.resolved_path
        if image_path is None:
            task.should_process = False
            task.reason = "image path could not be resolved"
            logs.append(f"Skipped: {task.reference.raw_path}; {task.reason}")
            continue

        mask_path = find_matching_mask(image_path, config.mask_dir)
        if mask_path is None:
            if dry_run and config.region and config.region != "none":
                task.reason = f"fallback area will generate mask: {config.region}"
                processable.append(task)
                logs.append(f"Ready: {task.reference.raw_path}; fallback area will generate mask={config.region}")
                continue
            mask_path = create_region_mask(image_path, config.region, generated_mask_dir)
        if mask_path is None:
            task.should_process = False
            task.reason = "mask missing"
            logs.append(f"Skipped: {task.reference.raw_path}; mask missing")
            continue
        if not mask_size_matches(image_path, mask_path):
            task.should_process = False
            task.reason = "mask size does not match image"
            task.mask_path = mask_path
            logs.append(f"Skipped: {task.reference.raw_path}; mask size does not match image")
            continue
        task.mask_path = mask_path
        processable.append(task)
        logs.append(f"Ready: {task.reference.raw_path}; mask={mask_path}")
    return processable


def _prepare_batch_files(tasks: list[ImageTask], batch_image_dir: Path, batch_mask_dir: Path, config: RunConfig) -> None:
    for index, task in enumerate(tasks, start=1):
        image_path = task.reference.resolved_path
        if image_path is None or task.mask_path is None:
            continue
        if config.progress_callback:
            config.progress_callback(
                ProgressEvent(stage="processing", message=f"Preparing image: {task.reference.raw_path}", current=index, total=len(tasks))
            )
        safe_name = f"{index:04d}-{_safe_stem(image_path.stem)}{image_path.suffix.lower()}"
        batch_image = batch_image_dir / safe_name
        batch_mask = batch_mask_dir / safe_name
        shutil.copy2(image_path, batch_image)
        shutil.copy2(task.mask_path, batch_mask)
        task.batch_image_path = batch_image
        task.batch_mask_path = batch_mask


def _planning_logs(tasks: list[ImageTask]) -> list[str]:
    logs = [f"Found {len(tasks)} Markdown image reference(s)."]
    for task in tasks:
        if task.should_process:
            logs.append(f"Will process: {task.reference.raw_path}")
        else:
            logs.append(f"Will skip: {task.reference.raw_path}; {task.reason}")
    return logs


def _safe_stem(stem: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in stem)
    return cleaned.strip("-_") or "image"


def _unique_name(directory: Path, name: str) -> str:
    candidate = name
    stem = Path(name).stem
    suffix = Path(name).suffix
    counter = 1
    while (directory / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _emit_progress(config: RunConfig, stage: str, message: str, tasks: list[ImageTask]) -> None:
    if config.progress_callback is None:
        return
    total = len(tasks)
    success_count = sum(1 for task in tasks if task.success)
    skipped_count = sum(1 for task in tasks if not task.should_process)
    failed_count = sum(1 for task in tasks if task.should_process and (task.error is not None or (stage == "complete" and not task.success)))
    current = min(total, success_count + skipped_count + failed_count)
    config.progress_callback(
        ProgressEvent(
            stage=stage,
            message=message,
            current=current,
            total=total,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )
    )
