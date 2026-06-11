from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from md_image_inpaint.desktop import check_environment
from md_image_inpaint.gui import main
from md_image_inpaint.models import ImageTask, RunConfig, RunResult
from md_image_inpaint.runner import run as run_processing


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Image Inpaint desktop app entrypoint.")
    parser.add_argument("--smoke-check", action="store_true", help="Check bundled desktop runtime without opening a window.")
    parser.add_argument(
        "--require-iopaint",
        action="store_true",
        help="Require the IOPaint command during --smoke-check.",
    )
    parser.add_argument("--process-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--markdown", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--mask-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--model-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.smoke_check:
        result = check_environment(require_iopaint=args.require_iopaint)
        print(result.user_message)
        for line in result.details:
            print(line)
        return 0 if result.ok else 1

    if args.process_smoke:
        return _run_process_smoke(args)

    main()
    return 0


def _run_process_smoke(args: argparse.Namespace) -> int:
    if args.markdown is None or args.out is None:
        print("--process-smoke requires --markdown and --out.", file=sys.stderr)
        return 2

    env = check_environment(require_iopaint=True)
    print(env.user_message)
    for line in env.details:
        print(line)
    if not env.ok:
        return 1

    source_hashes = _hash_sources(args.markdown)
    config = RunConfig(
        markdown_path=args.markdown,
        out_dir=args.out,
        mask_dir=args.mask_dir,
        model_dir=args.model_dir,
        dry_run=False,
        verbose=True,
        iopaint_cmd=env.iopaint_cmd or "iopaint",
    )
    result = run_processing(config)
    for line in result.logs:
        print(line)

    failures = _process_smoke_failures(result, source_hashes)
    if failures:
        print("Process smoke failed; " + "; ".join(failures) + ".", file=sys.stderr)
        return 1

    print(f"Process smoke passed: {result.output_markdown_path}")
    return 0


def _process_smoke_failures(result: RunResult, source_hashes: dict[Path, str]) -> list[str]:
    failures: list[str] = []
    output_markdown_path = result.output_markdown_path
    if output_markdown_path is None or not output_markdown_path.exists():
        failures.append("missing output Markdown")
    if result.log_path is None or not result.log_path.exists():
        failures.append("missing run log")
    if result.success_count < 1:
        failures.append("no processed image was reported")
    if not result.output_images_dir.exists():
        failures.append("missing output image folder")
    elif not _has_file(result.output_images_dir):
        failures.append("output image folder is empty")

    if output_markdown_path is not None:
        backup_root = output_markdown_path.parent / "backups"
        original_backup = backup_root / "original.md"
        backup_images_dir = backup_root / "images"
        if not original_backup.exists():
            failures.append("missing original Markdown backup")
        if not backup_images_dir.exists():
            failures.append("missing backup image folder")
        elif not _has_file(backup_images_dir):
            failures.append("backup image folder is empty")

    for task in _successful_tasks(result.tasks):
        if task.output_path is None or not task.output_path.exists():
            failures.append(f"missing processed image for {task.reference.raw_path}")
        if task.backup_path is None or not task.backup_path.exists():
            failures.append(f"missing source image backup for {task.reference.raw_path}")

    for source_path, expected_hash in source_hashes.items():
        if not source_path.exists():
            failures.append(f"source file disappeared: {source_path}")
        elif _file_hash(source_path) != expected_hash:
            failures.append(f"source file changed: {source_path}")
    return failures


def _successful_tasks(tasks: list[ImageTask]) -> list[ImageTask]:
    return [task for task in tasks if task.success]


def _hash_sources(markdown_path: Path) -> dict[Path, str]:
    sources = {markdown_path.resolve(): _file_hash(markdown_path)}
    markdown_text = markdown_path.read_text(encoding="utf-8")
    from md_image_inpaint.markdown import build_tasks

    for task in build_tasks(markdown_text, markdown_path):
        image_path = task.reference.resolved_path
        if image_path is not None and image_path.exists():
            sources[image_path.resolve()] = _file_hash(image_path)
    return sources


def _has_file(directory: Path) -> bool:
    return any(path.is_file() for path in directory.iterdir())


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
