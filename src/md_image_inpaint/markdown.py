from __future__ import annotations

import re
from pathlib import Path

from .models import ImageReference, ImageTask, is_remote_path


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def extract_markdown_path(target_text: str) -> str:
    """Extract the image path from a Markdown image target."""
    text = target_text.strip()
    if text.startswith("<") and ">" in text:
        return text[1 : text.index(">")]
    if " " in text:
        return text.split(" ", 1)[0]
    return text


def parse_markdown_images(markdown_text: str, markdown_path: Path) -> list[ImageReference]:
    base_dir = markdown_path.resolve().parent
    refs: list[ImageReference] = []
    for match in IMAGE_RE.finditer(markdown_text):
        raw_path = extract_markdown_path(match.group(2))
        remote = is_remote_path(raw_path)
        resolved = None
        exists = False
        if not remote:
            candidate = Path(raw_path)
            resolved = candidate if candidate.is_absolute() else base_dir / candidate
            resolved = resolved.resolve()
            exists = resolved.exists()
        refs.append(
            ImageReference(
                alt=match.group(1),
                raw_path=raw_path,
                original_text=match.group(0),
                start=match.start(),
                end=match.end(),
                is_remote=remote,
                resolved_path=resolved,
                exists=exists,
            )
        )
    return refs


def build_tasks(markdown_text: str, markdown_path: Path) -> list[ImageTask]:
    tasks: list[ImageTask] = []
    for ref in parse_markdown_images(markdown_text, markdown_path):
        if ref.is_remote:
            tasks.append(ImageTask(ref, False, "remote image skipped"))
        elif not ref.exists:
            tasks.append(ImageTask(ref, False, "local image does not exist"))
        else:
            tasks.append(ImageTask(ref, True, "ready"))
    return tasks


def rewrite_markdown(markdown_text: str, tasks: list[ImageTask], output_doc_dir: Path) -> str:
    replacements: list[tuple[int, int, str]] = []
    for task in tasks:
        if not task.success or task.output_path is None:
            continue
        rel_path = task.output_path.resolve().relative_to(output_doc_dir.resolve()).as_posix()
        replacement = f"![{task.reference.alt}]({rel_path})"
        replacements.append((task.reference.start, task.reference.end, replacement))

    rewritten = markdown_text
    for start, end, replacement in sorted(replacements, reverse=True):
        rewritten = rewritten[:start] + replacement + rewritten[end:]
    return rewritten
