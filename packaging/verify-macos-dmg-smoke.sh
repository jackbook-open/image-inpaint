#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

DMG_PATH="release/ImageInpaint-macOS.dmg"
MOUNT_POINT="${MOUNT_POINT:-dist/dmg-smoke-mount}"
REQUIRE_IOPAINT=0

for arg in "$@"; do
  case "$arg" in
    --require-iopaint) REQUIRE_IOPAINT=1 ;;
    --*) echo "Unknown option: $arg" >&2; exit 2 ;;
    *) DMG_PATH="$arg" ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS dmg smoke must run on macOS." >&2
  exit 1
fi
if [[ ! -f "$DMG_PATH" ]]; then
  echo "Missing dmg: $DMG_PATH" >&2
  exit 2
fi
python3 packaging/verify-checksum.py "$DMG_PATH"

cleanup() {
  hdiutil detach "$MOUNT_POINT" -quiet || true
  rm -rf "$MOUNT_POINT"
}
trap cleanup EXIT

rm -rf "$MOUNT_POINT"
mkdir -p "$MOUNT_POINT"

hdiutil verify "$DMG_PATH"
hdiutil attach "$DMG_PATH" -mountpoint "$MOUNT_POINT" -nobrowse -quiet

test -d "$MOUNT_POINT/ImageInpaint.app"
test -L "$MOUNT_POINT/Applications"
test -f "$MOUNT_POINT/README.txt"
grep -q "authorized to modify" "$MOUNT_POINT/README.txt"

APP_EXE="$MOUNT_POINT/ImageInpaint.app/Contents/MacOS/ImageInpaint"
SMOKE_EXE="$MOUNT_POINT/ImageInpaint.app/Contents/MacOS/ImageInpaintSmoke"
if [[ ! -x "$APP_EXE" ]]; then
  echo "Missing app executable in dmg: $APP_EXE" >&2
  exit 1
fi
if [[ ! -x "$SMOKE_EXE" ]]; then
  SMOKE_EXE="$APP_EXE"
fi

if [[ "$REQUIRE_IOPAINT" == "1" ]]; then
  "$SMOKE_EXE" --smoke-check --require-iopaint
else
  "$SMOKE_EXE" --smoke-check
fi

echo "macOS dmg smoke passed."
