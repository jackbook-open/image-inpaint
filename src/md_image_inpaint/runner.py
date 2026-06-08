from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .engine import EngineError, run_engine
from .markdown import build_tasks, rewrite_markdown
from .masks import create_region_mask, find_matching_mask
from .models import ImageTask, RunConfig, RunResult, matches_skip_pattern


def run(config: RunConfig) -> RunResult:
    markdown_path = config.markdown_path.resolve()
    markdown_text = markdown_path.read_text(encoding="utf-8")
    out_dir = config.out_dir.resolve()
    output_images_dir = out_dir / "images"
    output_markdown_path = out_dir / "document.md"

    tasks = build_tasks(markdown_text, markdown_path)
    _apply_skip_patterns(tasks, config.skip_patterns)
    logs: list[str] = [f"Scanning Markdown: {markdown_path}"]
    logs.extend(_planning_logs(tasks))

    if config.dry_run:
        return RunResult(
            markdown_path=markdown_path,
            output_markdown_path=None,
            output_images_dir=output_images_dir,
            tasks=tasks,
            logs=logs + ["Dry run enabled; no files were written."],
            skipped_count=sum(1 for task in tasks if not task.should_process),
        )

    _prepare_output_dirs(out_dir)
    _backup_sources(markdown_path, tasks, out_dir, logs)

    generated_mask_dir = out_dir / "generated_masks"
    processable = _attach_masks(tasks, config, generated_mask_dir, logs)

    if processable:
        with tempfile.TemporaryDirectory(prefix="md-image-inpaint-") as tmp:
            tmp_dir = Path(tmp)
            batch_image_dir = tmp_dir / "images"
            batch_mask_dir = tmp_dir / "masks"
            batch_image_dir.mkdir()
            batch_mask_dir.mkdir()
            _prepare_batch_files(processable, batch_image_dir, batch_mask_dir)
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

    rewritten = rewrite_markdown(markdown_text, tasks, out_dir)
    output_markdown_path.write_text(rewritten, encoding="utf-8")
    logs.append(f"Wrote Markdown: {output_markdown_path}")

    success_count = sum(1 for task in tasks if task.success)
    failed_count = sum(1 for task in tasks if task.should_process and not task.success)
    skipped_count = sum(1 for task in tasks if not task.should_process)
    return RunResult(
        markdown_path=markdown_path,
        output_markdown_path=output_markdown_path,
        output_images_dir=output_images_dir,
        tasks=tasks,
        logs=logs,
        success_count=success_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
    )


def _prepare_output_dirs(out_dir: Path) -> None:
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "backups" / "images").mkdir(parents=True, exist_ok=True)


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


def _attach_masks(tasks: list[ImageTask], config: RunConfig, generated_mask_dir: Path, logs: list[str]) -> list[ImageTask]:
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
            mask_path = create_region_mask(image_path, config.region, generated_mask_dir)
        if mask_path is None:
            task.should_process = False
            task.reason = "mask missing"
            logs.append(f"Skipped: {task.reference.raw_path}; mask missing")
            continue
        task.mask_path = mask_path
        processable.append(task)
        logs.append(f"Ready: {task.reference.raw_path}; mask={mask_path}")
    return processable


def _prepare_batch_files(tasks: list[ImageTask], batch_image_dir: Path, batch_mask_dir: Path) -> None:
    for index, task in enumerate(tasks, start=1):
        image_path = task.reference.resolved_path
        if image_path is None or task.mask_path is None:
            continue
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
