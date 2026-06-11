#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_PATH="${1:-dist/ImageInpaint.app}"
RUNTIME_DIR="${RUNTIME_DIR:-fake-iopaint-runtime}"
OUT_DIR="${OUT_DIR:-packaged-process-smoke-output}"

APP_EXE="$APP_PATH/Contents/MacOS/ImageInpaint"
if [[ ! -x "$APP_EXE" ]]; then
  APP_EXE="dist/ImageInpaint/ImageInpaint"
fi
if [[ ! -x "$APP_EXE" ]]; then
  echo "Could not find packaged app executable for $APP_PATH" >&2
  exit 1
fi

SMOKE_EXE="$(dirname "$APP_EXE")/ImageInpaintSmoke"
if [[ ! -x "$SMOKE_EXE" && -x "dist/ImageInpaint/ImageInpaintSmoke" ]]; then
  SMOKE_EXE="dist/ImageInpaint/ImageInpaintSmoke"
fi
if [[ ! -x "$SMOKE_EXE" ]]; then
  SMOKE_EXE="$APP_EXE"
fi

if [[ ! -x "$RUNTIME_DIR/iopaint" ]]; then
  bash ./packaging/make-fake-iopaint-runtime.sh "$RUNTIME_DIR"
fi

rm -rf "$OUT_DIR"
IMAGE_INPAINT_RUNTIME_DIR="$(cd "$RUNTIME_DIR" && pwd)" \
  "$SMOKE_EXE" \
  --process-smoke \
  --markdown "examples/document.md" \
  --out "$OUT_DIR" \
  --mask-dir "examples/masks" \
  --model-dir ".model-cache"

rm -rf "$OUT_DIR"
echo "Packaged process smoke passed."
