#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

NO_IOPAINT=0
SKIP_SMOKE=0
RUNTIME_DIR=""
PYTHON_COMMAND="${PYTHON_COMMAND:-python3}"
for arg in "$@"; do
  case "$arg" in
    --no-iopaint) NO_IOPAINT=1 ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
    --runtime-dir=*) RUNTIME_DIR="${arg#*=}" ;;
    --python=*) PYTHON_COMMAND="${arg#*=}" ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [[ ! -x ".venv/bin/python" ]]; then
  "$PYTHON_COMMAND" -m venv .venv
fi

PYTHON=".venv/bin/python"
"$PYTHON" -m pip install --upgrade pip

if [[ "$NO_IOPAINT" == "1" || -n "$RUNTIME_DIR" ]]; then
  "$PYTHON" -m pip install -e ".[desktop]"
else
  "$PYTHON" -m pip install -e ".[desktop,iopaint]"
fi

"$PYTHON" -m PyInstaller --noconfirm "packaging/pyinstaller-image-inpaint.spec"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS .app/.dmg packaging must be run on macOS." >&2
  exit 1
fi

if [[ ! -f "packaging/macos-entitlements.plist" ]]; then
  echo "Missing macOS entitlements file: packaging/macos-entitlements.plist" >&2
  exit 1
fi

if [[ -n "$RUNTIME_DIR" ]]; then
  RUNTIME_DIR="$(cd "$RUNTIME_DIR" && pwd)"
  rm -rf "dist/ImageInpaint/runtime" "dist/ImageInpaint.app/Contents/MacOS/runtime"
  cp -R "$RUNTIME_DIR" "dist/ImageInpaint/runtime"
  mkdir -p "dist/ImageInpaint.app/Contents/MacOS"
  cp -R "$RUNTIME_DIR" "dist/ImageInpaint.app/Contents/MacOS/runtime"
  echo "Bundled runtime: $RUNTIME_DIR"
fi

if [[ "$SKIP_SMOKE" != "1" ]]; then
  APP_EXE="dist/ImageInpaint.app/Contents/MacOS/ImageInpaint"
  if [[ ! -x "$APP_EXE" ]]; then
    APP_EXE="dist/ImageInpaint/ImageInpaint"
  fi
  if [[ ! -x "$APP_EXE" ]]; then
    echo "Could not find packaged app executable for smoke check." >&2
    exit 1
  fi
  SMOKE_EXE="$(dirname "$APP_EXE")/ImageInpaintSmoke"
  if [[ ! -x "$SMOKE_EXE" && -x "dist/ImageInpaint/ImageInpaintSmoke" ]]; then
    SMOKE_EXE="dist/ImageInpaint/ImageInpaintSmoke"
  fi
  if [[ ! -x "$SMOKE_EXE" ]]; then
    SMOKE_EXE="$APP_EXE"
  fi
  if [[ "$NO_IOPAINT" == "1" ]]; then
    "$SMOKE_EXE" --smoke-check
  else
    "$SMOKE_EXE" --smoke-check --require-iopaint
  fi
fi

mkdir -p release
DMG_PATH="release/ImageInpaint-macOS.dmg"
DMG_ROOT="dist/dmg-root"
rm -f "$DMG_PATH"
rm -rf "$DMG_ROOT"
mkdir -p "$DMG_ROOT"
cp -R "dist/ImageInpaint.app" "$DMG_ROOT/ImageInpaint.app"
ln -s /Applications "$DMG_ROOT/Applications"
cat > "$DMG_ROOT/README.txt" <<'EOF'
Image Inpaint

Drag ImageInpaint.app to Applications, then open it from Applications.

Use this app only on documents and images that you own or are explicitly
authorized to modify. Do not use it to remove third-party copyright notices,
attribution, source marks, signatures, or other protected content.
EOF

hdiutil create -volname "Image Inpaint" -srcfolder "$DMG_ROOT" -ov -format UDZO "$DMG_PATH"
python3 packaging/verify-checksum.py --write "$DMG_PATH"

echo ""
echo "Build complete: dist/ImageInpaint.app"
echo "Release package: $DMG_PATH"
echo "Checksum: $DMG_PATH.sha256"
echo "Run open release/ImageInpaint-macOS.dmg to test the installer layout."
