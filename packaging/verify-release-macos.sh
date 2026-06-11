#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_PATH="${1:-dist/ImageInpaint.app}"
OUT_DIR="${OUT_DIR:-release-smoke-output}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS release verification must run on macOS." >&2
  exit 1
fi

APP_EXE="$APP_PATH/Contents/MacOS/ImageInpaint"
if [[ ! -x "$APP_EXE" ]]; then
  APP_EXE="dist/ImageInpaint/ImageInpaint"
fi
if [[ ! -x "$APP_EXE" ]]; then
  echo "Could not find packaged app executable for $APP_PATH" >&2
  exit 1
fi
SMOKE_EXE="$(dirname "$APP_EXE")/ImageInpaintSmoke"
if [[ ! -x "$SMOKE_EXE" ]]; then
  SMOKE_EXE="$APP_EXE"
fi

if [[ ! -f "packaging/macos-entitlements.plist" ]]; then
  echo "Missing macOS entitlements file: packaging/macos-entitlements.plist" >&2
  exit 1
fi

"$SMOKE_EXE" --smoke-check --require-iopaint

rm -rf "$OUT_DIR"

"$SMOKE_EXE" \
  --process-smoke \
  --markdown "examples/document.md" \
  --out "$OUT_DIR" \
  --mask-dir "examples/masks" \
  --model-dir ".model-cache"

test -f "$OUT_DIR/document.md"
find "$OUT_DIR/images" -type f -print -quit | grep -q .
test -f "$OUT_DIR/backups/original.md"
find "$OUT_DIR/backups/images" -type f -print -quit | grep -q .
test -f "$OUT_DIR/logs/run.log"

echo "Release verification passed."
echo "Output Markdown: $OUT_DIR/document.md"
echo "Output images: $OUT_DIR/images"
echo "Backups: $OUT_DIR/backups"
echo "Run log: $OUT_DIR/logs/run.log"
