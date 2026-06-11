from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_repository_boundary_verifier_passes_for_tracked_files() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "packaging" / "verify-repository-boundaries.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert result.returncode == 0, result.stdout
    assert "Repository boundary check passed." in result.stdout
