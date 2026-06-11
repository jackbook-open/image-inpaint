from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata
from pathlib import Path


APP_NAME = "Image Inpaint"
APP_DIR_NAME = "image-inpaint"
RUNTIME_ENV_VAR = "IMAGE_INPAINT_RUNTIME_DIR"
MIN_MODEL_CACHE_FREE_BYTES = 2 * 1024 * 1024 * 1024


@dataclass
class EnvironmentCheck:
    ok: bool
    user_message: str
    details: list[str] = field(default_factory=list)
    iopaint_cmd: str | None = None


def app_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME


def default_output_parent() -> Path:
    documents = Path.home() / "Documents"
    if documents.exists():
        return documents / APP_NAME / "Outputs"
    return app_data_dir() / "outputs"


def default_output_dir(markdown_path: Path | None = None, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    stem = _safe_name(markdown_path.stem if markdown_path else "document")
    return default_output_parent() / f"{stem}-{timestamp}"


def default_model_dir() -> Path:
    return app_data_dir() / "model-cache"


def check_environment(iopaint_cmd: str = "iopaint", require_iopaint: bool = True) -> EnvironmentCheck:
    details: list[str] = [
        f"System: {platform.system()} {platform.release()}",
        f"Python: {platform.python_version()}",
    ]
    missing: list[str] = []
    for package, importer in _runtime_imports().items():
        try:
            version = _package_version(package)
            importer()
            details.append(f"{package}: {version}")
        except Exception as exc:  # noqa: BLE001 - any import failure makes the runtime unusable.
            missing.append(package)
            details.append(f"{package}: unavailable ({exc})")

    iopaint_path = resolve_iopaint_command(iopaint_cmd)
    if iopaint_path:
        details.append(f"IOPaint runtime: {iopaint_path}")
    elif require_iopaint:
        missing.append("IOPaint runtime")
        details.append("IOPaint runtime: not found")
    else:
        details.append("IOPaint runtime: not required for pre-check")

    model_dir = default_model_dir()
    try:
        model_dir.mkdir(parents=True, exist_ok=True)
        details.append(f"Model cache: {model_dir}")
        free_bytes = _free_bytes(model_dir)
        details.append(f"Model cache free space: {_format_bytes(free_bytes)}")
        details.append(
            "First processing run may download the inpainting model into this cache; progress and retry details appear in the app log."
        )
        if free_bytes < MIN_MODEL_CACHE_FREE_BYTES:
            missing.append("free model cache space")
            details.append(
                f"Model cache needs at least {_format_bytes(MIN_MODEL_CACHE_FREE_BYTES)} free for first-run model preparation."
            )
    except OSError as exc:
        missing.append("writable model cache")
        details.append(f"Model cache error: {exc}")

    if missing:
        return EnvironmentCheck(
            ok=False,
            user_message="Some required desktop runtime components are not ready.",
            details=[f"Missing or unavailable: {', '.join(missing)}", *details],
            iopaint_cmd=iopaint_path,
        )
    return EnvironmentCheck(ok=True, user_message="Desktop runtime check passed.", details=details, iopaint_cmd=iopaint_path)


def resolve_iopaint_command(preferred: str = "iopaint") -> str | None:
    candidates: list[Path | str] = []
    runtime_dir = os.environ.get(RUNTIME_ENV_VAR)
    if runtime_dir:
        candidates.extend(_iopaint_candidates(Path(runtime_dir)))
    for base in _app_runtime_dirs():
        candidates.extend(_iopaint_candidates(base))
    candidates.append(preferred)

    for candidate in candidates:
        text = str(candidate)
        if Path(text).is_absolute() or any(sep in text for sep in ("/", "\\")):
            if Path(text).exists():
                return str(Path(text).resolve())
            continue
        found = shutil.which(text)
        if found:
            return found
    return None


def clear_model_cache(model_dir: Path | None = None) -> Path:
    target = (model_dir or default_model_dir()).resolve()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def open_path(path: Path) -> None:
    target = path.resolve()
    if platform.system() == "Windows":
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def human_summary(success_count: int, skipped_count: int, failed_count: int) -> str:
    return f"Processed {success_count}; skipped {skipped_count}; failed {failed_count}."


def _free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    return cleaned.strip("-_") or "document"


def _app_runtime_dirs() -> list[Path]:
    bases = [Path(sys.executable).resolve().parent]
    if getattr(sys, "frozen", False):
        bases.append(Path(sys.executable).resolve().parent / "_internal")
    bases.append(Path(__file__).resolve().parents[2])
    dirs: list[Path] = []
    for base in bases:
        dirs.extend([base / "runtime", base / "iopaint-runtime", base])
    return dirs


def _iopaint_candidates(base: Path) -> list[Path]:
    if platform.system() == "Windows":
        names = ("iopaint.exe", "iopaint.cmd", "iopaint.bat", "Scripts/iopaint.exe", "Scripts/iopaint.cmd")
    else:
        names = ("iopaint", "bin/iopaint")
    return [base / name for name in names]


def _runtime_imports() -> dict[str, Callable[[], object]]:
    return {
        "Pillow": lambda: __import__("PIL.Image"),
        "PyYAML": lambda: __import__("yaml"),
    }


def _package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "bundled"
