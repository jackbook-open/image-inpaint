from __future__ import annotations

import argparse
from pathlib import Path

from .config import merge_config
from .masks import REGIONS
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m md_image_inpaint",
        description="Batch inpaint local images referenced by a Markdown document.",
    )
    parser.add_argument("markdown", nargs="?", type=Path, help="Path to one Markdown file.")
    parser.add_argument("--out", dest="out_dir", type=Path, help="Output directory.")
    parser.add_argument("--mask-dir", type=Path, help="Directory containing masks matched by image filename.")
    parser.add_argument("--region", choices=REGIONS, help="Generate a fixed region mask when no mask file matches.")
    parser.add_argument("--engine", default=None, choices=["iopaint"], help="Inpainting engine. Default: iopaint.")
    parser.add_argument("--device", default=None, help="IOPaint device, for example cpu or cuda. Default: cpu.")
    parser.add_argument("--model", default=None, help="IOPaint model. Default: lama.")
    parser.add_argument("--model-dir", type=Path, default=None, help="IOPaint model cache/download directory.")
    parser.add_argument("--config", type=Path, help="YAML config file.")
    parser.add_argument("--dry-run", action="store_true", default=None, help="List planned work without writing files.")
    parser.add_argument("--verbose", action="store_true", default=None, help="Print detailed logs.")
    parser.add_argument("--iopaint-cmd", default=None, help="Path or command name for the IOPaint executable.")
    parser.add_argument(
        "--skip-pattern",
        dest="skip_patterns",
        action="append",
        help="Glob pattern for Markdown image paths to skip. Can be used more than once.",
    )
    parser.add_argument("--gui", action="store_true", help="Open the graphical interface instead of running the CLI.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.gui:
        from .gui import main as gui_main

        gui_main()
        return 0

    if args.markdown is None:
        parser.error("Markdown file is required unless --gui is used.")
    if not args.markdown.exists():
        parser.error(f"Markdown file not found: {args.markdown}")
    cli_values = {
        "out_dir": args.out_dir,
        "mask_dir": args.mask_dir,
        "region": args.region,
        "engine": args.engine,
        "device": args.device,
        "model": args.model,
        "model_dir": args.model_dir,
        "dry_run": args.dry_run,
        "verbose": args.verbose,
        "iopaint_cmd": args.iopaint_cmd,
        "skip_patterns": args.skip_patterns,
    }
    config = merge_config(args.markdown, cli_values, args.config)
    result = run(config)
    for line in result.logs:
        print(line)
    if result.output_markdown_path is not None:
        print(f"Output Markdown: {result.output_markdown_path}")
        print(f"Images: {result.output_images_dir}")
        print(f"Summary: processed={result.success_count}, skipped={result.skipped_count}, failed={result.failed_count}")
    return 1 if result.failed_count else 0
