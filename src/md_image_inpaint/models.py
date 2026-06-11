from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from threading import Event
from typing import Callable


REMOTE_PREFIXES = ("http://", "https://", "ftp://", "data:")


@dataclass(frozen=True)
class ImageReference:
    alt: str
    raw_path: str
    original_text: str
    start: int
    end: int
    is_remote: bool
    resolved_path: Path | None
    exists: bool


@dataclass
class ImageTask:
    reference: ImageReference
    should_process: bool
    reason: str
    mask_path: Path | None = None
    output_path: Path | None = None
    backup_path: Path | None = None
    batch_image_path: Path | None = None
    batch_mask_path: Path | None = None
    success: bool = False
    error: str | None = None


@dataclass
class RunConfig:
    markdown_path: Path
    out_dir: Path
    mask_dir: Path | None = None
    region: str | None = None
    engine: str = "iopaint"
    device: str = "cpu"
    model: str = "lama"
    model_dir: Path | None = None
    dry_run: bool = False
    verbose: bool = False
    iopaint_cmd: str = "iopaint"
    skip_patterns: list[str] = field(default_factory=list)
    cancel_token: "CancelToken | None" = None
    progress_callback: "ProgressCallback | None" = None


@dataclass
class RunResult:
    markdown_path: Path
    output_markdown_path: Path | None
    output_images_dir: Path
    log_path: Path | None = None
    tasks: list[ImageTask] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    success_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    dry_run: bool = False


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    message: str
    current: int = 0
    total: int = 0
    success_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0


ProgressCallback = Callable[[ProgressEvent], None]


def is_remote_path(path_text: str) -> bool:
    return path_text.lower().startswith(REMOTE_PREFIXES)


def matches_skip_pattern(path_text: str, patterns: list[str]) -> str | None:
    normalized = path_text.replace("\\", "/")
    for pattern in patterns:
        if fnmatch(normalized, pattern.replace("\\", "/")):
            return pattern
    return None


class CancelToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()
