#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUNTIME_DIR="iopaint-runtime"
PYTHON_COMMAND="${PYTHON_COMMAND:-python3}"
TORCH_INDEX_URL=""
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --runtime-dir=*) RUNTIME_DIR="${arg#*=}" ;;
    --python=*) PYTHON_COMMAND="${arg#*=}" ;;
    --torch-index-url=*) TORCH_INDEX_URL="${arg#*=}" ;;
    --force) FORCE=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

assert_compatible_python() {
  "$1" - <<'PY'
import struct
import sys

major, minor = sys.version_info[:2]
bits = struct.calcsize("P") * 8
print(f"Python {major}.{minor}.{sys.version_info.micro} ({bits}-bit) at {sys.executable}")
if bits != 64:
    raise SystemExit("IOPaint/PyTorch runtime builds require 64-bit Python.")
if (major, minor) < (3, 10) or (major, minor) >= (3, 13):
    raise SystemExit("Use Python 3.10, 3.11, or 3.12 for IOPaint/PyTorch runtime builds.")
PY
}

assert_runtime_imports() {
  "$1" - <<'PY'
import importlib.metadata as metadata
import torch

print("torch:", metadata.version("torch"))
print("iopaint:", metadata.version("iopaint"))
PY
}

if [[ -e "$RUNTIME_DIR" ]]; then
  if [[ "$FORCE" != "1" ]]; then
    echo "Runtime directory already exists: $RUNTIME_DIR. Re-run with --force to replace it." >&2
    exit 1
  fi
  rm -rf "$RUNTIME_DIR"
fi

assert_compatible_python "$PYTHON_COMMAND"
"$PYTHON_COMMAND" -m venv "$RUNTIME_DIR"
RUNTIME_PYTHON="$RUNTIME_DIR/bin/python"
assert_compatible_python "$RUNTIME_PYTHON"
"$RUNTIME_PYTHON" -m pip install --upgrade pip

if [[ -n "$TORCH_INDEX_URL" ]]; then
  "$RUNTIME_PYTHON" -m pip install "iopaint>=1.5.0" --extra-index-url "$TORCH_INDEX_URL"
else
  "$RUNTIME_PYTHON" -m pip install "iopaint>=1.5.0"
fi

assert_runtime_imports "$RUNTIME_PYTHON"

cat > "$RUNTIME_DIR/iopaint" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$RUNTIME_DIR/bin/python" -m iopaint "$@"
EOF
chmod +x "$RUNTIME_DIR/iopaint"

"$RUNTIME_DIR/iopaint" --help >/dev/null

echo ""
echo "IOPaint runtime prepared: $PROJECT_ROOT/$RUNTIME_DIR"
echo "Build with: ./packaging/build-macos.sh --runtime-dir=$PROJECT_ROOT/$RUNTIME_DIR"
