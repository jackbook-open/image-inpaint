from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def test_checksum_verifier_accepts_matching_sidecar(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"desktop release artifact")
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.with_suffix(".bin.sha256").write_text(f"{checksum}  artifact.bin\n", encoding="utf-8")

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "packaging/verify-checksum.py", str(artifact)],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert result.returncode == 0, result.stdout
    assert "Checksum verified" in result.stdout


def test_checksum_verifier_rejects_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"desktop release artifact")
    checksum = "0" * 64
    artifact.with_suffix(".bin.sha256").write_text(f"{checksum}  artifact.bin\n", encoding="utf-8")

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "packaging/verify-checksum.py", str(artifact)],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert result.returncode == 1
    assert "Checksum mismatch" in result.stdout


def test_checksum_verifier_write_uses_current_artifact_name(tmp_path: Path) -> None:
    artifact = tmp_path / "renamed-artifact.dmg"
    artifact.write_bytes(b"desktop release artifact")

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "packaging/verify-checksum.py", "--write", str(artifact)],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    checksum_text = Path(f"{artifact}.sha256").read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout
    assert checksum_text.endswith("  renamed-artifact.dmg\n")
    assert "Checksum verified" in result.stdout
