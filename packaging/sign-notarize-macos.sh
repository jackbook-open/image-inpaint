#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_PATH="${APP_PATH:-dist/ImageInpaint.app}"
DMG_PATH="${DMG_PATH:-release/ImageInpaint-macOS.dmg}"
SIGNED_DMG_PATH="${SIGNED_DMG_PATH:-release/ImageInpaint-macOS-notarized.dmg}"
ENTITLEMENTS_PATH="${ENTITLEMENTS_PATH:-packaging/macos-entitlements.plist}"
IDENTITY="${APPLE_DEVELOPER_ID_APPLICATION:-}"
KEYCHAIN_PROFILE="${APPLE_NOTARY_KEYCHAIN_PROFILE:-}"
APPLE_ID="${APPLE_ID:-}"
APPLE_TEAM_ID="${APPLE_TEAM_ID:-}"
APPLE_APP_SPECIFIC_PASSWORD="${APPLE_APP_SPECIFIC_PASSWORD:-}"

usage() {
  cat <<'EOF'
Usage:
  APPLE_DEVELOPER_ID_APPLICATION="Developer ID Application: Name (TEAMID)" \
  APPLE_NOTARY_KEYCHAIN_PROFILE="profile-name" \
  ./packaging/sign-notarize-macos.sh

Or provide Apple ID credentials:

  APPLE_DEVELOPER_ID_APPLICATION="Developer ID Application: Name (TEAMID)" \
  APPLE_ID="name@example.com" \
  APPLE_TEAM_ID="TEAMID" \
  APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
  ./packaging/sign-notarize-macos.sh

Optional paths:
  APP_PATH=dist/ImageInpaint.app
  DMG_PATH=release/ImageInpaint-macOS.dmg
  SIGNED_DMG_PATH=release/ImageInpaint-macOS-notarized.dmg
  ENTITLEMENTS_PATH=packaging/macos-entitlements.plist
EOF
}

require_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macOS signing and notarization must run on macOS." >&2
    exit 1
  fi
}

require_inputs() {
  if [[ -z "$IDENTITY" ]]; then
    echo "Missing APPLE_DEVELOPER_ID_APPLICATION." >&2
    usage >&2
    exit 2
  fi
  if [[ ! -d "$APP_PATH" ]]; then
    echo "Missing app bundle: $APP_PATH" >&2
    exit 2
  fi
  if [[ ! -f "$ENTITLEMENTS_PATH" ]]; then
    echo "Missing hardened runtime entitlements file: $ENTITLEMENTS_PATH" >&2
    exit 2
  fi
  if [[ -z "$KEYCHAIN_PROFILE" ]]; then
    if [[ -z "$APPLE_ID" || -z "$APPLE_TEAM_ID" || -z "$APPLE_APP_SPECIFIC_PASSWORD" ]]; then
      echo "Missing notarization credentials. Set APPLE_NOTARY_KEYCHAIN_PROFILE or APPLE_ID, APPLE_TEAM_ID, and APPLE_APP_SPECIFIC_PASSWORD." >&2
      usage >&2
      exit 2
    fi
  fi
}

submit_for_notarization() {
  if [[ -n "$KEYCHAIN_PROFILE" ]]; then
    xcrun notarytool submit "$SIGNED_DMG_PATH" --keychain-profile "$KEYCHAIN_PROFILE" --wait
  else
    xcrun notarytool submit "$SIGNED_DMG_PATH" \
      --apple-id "$APPLE_ID" \
      --team-id "$APPLE_TEAM_ID" \
      --password "$APPLE_APP_SPECIFIC_PASSWORD" \
      --wait
  fi
}

create_dmg() {
  local src_root="dist/notarize-dmg-root"
  rm -rf "$src_root" "$SIGNED_DMG_PATH"
  mkdir -p "$src_root"
  cp -R "$APP_PATH" "$src_root/ImageInpaint.app"
  ln -s /Applications "$src_root/Applications"
  if [[ -f "dist/dmg-root/README.txt" ]]; then
    cp "dist/dmg-root/README.txt" "$src_root/README.txt"
  fi
  hdiutil create -volname "Image Inpaint" -srcfolder "$src_root" -ov -format UDZO "$SIGNED_DMG_PATH"
}

require_macos
require_inputs

echo "Signing app bundle: $APP_PATH"
codesign --force --deep --options runtime --timestamp --entitlements "$ENTITLEMENTS_PATH" --sign "$IDENTITY" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
spctl --assess --type execute --verbose=2 "$APP_PATH" || true

echo "Creating signed disk image: $SIGNED_DMG_PATH"
create_dmg
codesign --force --timestamp --sign "$IDENTITY" "$SIGNED_DMG_PATH"
codesign --verify --verbose=2 "$SIGNED_DMG_PATH"

echo "Submitting disk image to Apple notarization service..."
submit_for_notarization

echo "Stapling notarization ticket..."
xcrun stapler staple "$SIGNED_DMG_PATH"
xcrun stapler validate "$SIGNED_DMG_PATH"
spctl --assess --type open --verbose=2 "$SIGNED_DMG_PATH" || true
python3 packaging/verify-checksum.py --write "$SIGNED_DMG_PATH"

echo ""
echo "Signed and notarized disk image: $SIGNED_DMG_PATH"
echo "Checksum: $SIGNED_DMG_PATH.sha256"
