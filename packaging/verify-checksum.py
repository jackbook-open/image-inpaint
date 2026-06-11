from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_hash(checksum_path: Path) -> str:
    text = checksum_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Checksum file is empty: {checksum_path}")
    token = text.split()[0].lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise ValueError(f"Checksum file does not start with a SHA256 hash: {checksum_path}")
    return token


def write_checksum(artifact: Path, checksum: Path) -> None:
    checksum.write_text(f"{sha256(artifact)}  {artifact.name}\n", encoding="ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a SHA256 checksum sidecar file.")
    parser.add_argument("artifact", type=Path, help="Artifact file to verify")
    parser.add_argument(
        "checksum",
        type=Path,
        nargs="?",
        help="Checksum file; defaults to ARTIFACT.sha256",
    )
    parser.add_argument("--write", action="store_true", help="Write the checksum file before verifying it")
    args = parser.parse_args(argv)

    artifact = args.artifact
    checksum = args.checksum or Path(f"{artifact}.sha256")
    if not artifact.is_file():
        print(f"Missing artifact: {artifact}", file=sys.stderr)
        return 2
    if args.write:
        write_checksum(artifact, checksum)
    if not checksum.is_file():
        print(f"Missing checksum file: {checksum}", file=sys.stderr)
        return 2

    try:
        expected = expected_hash(checksum)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    actual = sha256(artifact)
    if actual != expected:
        print(f"Checksum mismatch for {artifact}", file=sys.stderr)
        print(f"Expected: {expected}", file=sys.stderr)
        print(f"Actual:   {actual}", file=sys.stderr)
        return 1

    print(f"Checksum verified: {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
