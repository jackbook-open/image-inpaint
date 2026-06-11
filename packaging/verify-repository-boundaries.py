from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MAX_TRACKED_FILE_BYTES = 25 * 1024 * 1024

BLOCKED_COMPONENTS = {
    ".model-cache",
    ".runtime",
    "build",
    "checkpoints",
    "dist",
    "fake-iopaint-runtime",
    "model_cache",
    "models",
    "output",
    "outputs",
    "packaged-process-smoke-output",
    "release",
    "release-smoke-output",
    "weights",
    "windows-install-smoke",
    "windows-installed-launch-smoke",
    "windows-zip-install-smoke",
}

BLOCKED_SUFFIXES = (
    ".case.md",
    ".ckpt",
    ".inpainted.md",
    ".local.md",
    ".onnx",
    ".private.md",
    ".pt",
    ".pth",
    ".safetensors",
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    names = result.stdout.decode("utf-8").split("\0")
    return [Path(name) for name in names if name]


def has_private_component(path: Path) -> bool:
    return any(part.startswith("_private") for part in path.parts)


def is_blocked_path(path: Path) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    lower_name = path.as_posix().lower()
    return (
        any(part in BLOCKED_COMPONENTS for part in lower_parts)
        or has_private_component(path)
        or lower_name.endswith(BLOCKED_SUFFIXES)
    )


def find_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for relative_path in tracked_files(root):
        if is_blocked_path(relative_path):
            violations.append(f"blocked tracked path: {relative_path.as_posix()}")
            continue

        absolute_path = root / relative_path
        if absolute_path.is_file() and absolute_path.stat().st_size > MAX_TRACKED_FILE_BYTES:
            size_mb = absolute_path.stat().st_size / (1024 * 1024)
            violations.append(f"tracked file is too large ({size_mb:.1f} MB): {relative_path.as_posix()}")

    return violations


def main() -> int:
    root = project_root()
    violations = find_violations(root)
    if violations:
        print("Repository boundary check failed.")
        print("Do not track runtimes, model weights, caches, release artifacts, or private user outputs.")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Repository boundary check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
