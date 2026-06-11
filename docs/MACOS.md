# macOS Guide

Supported targets: Apple Silicon and Intel macOS. Build each architecture on a
matching macOS runner, or use a release process that creates and tests universal
packages.

The packaging script creates `release/ImageInpaint-macOS.dmg` when run on macOS.
The release workflows build separate downloadable artifacts for Apple Silicon
and Intel Macs. Production releases should be signed and notarized before
distribution. The release workflow can do this when `notarize_macos` is enabled
and Apple Developer credentials are configured.

## Install and Launch

1. Download the macOS package for your Mac:
   `ImageInpaint-macOS-arm64` for Apple Silicon or
   `ImageInpaint-macOS-intel` for Intel.
2. Open `ImageInpaint-macOS.dmg`.
3. Drag `ImageInpaint.app` to the `Applications` shortcut shown in the disk
   image.
4. Open `Image Inpaint` from Applications.
5. If Gatekeeper reports that the app is from an unidentified developer, stop
   and confirm you downloaded a development build. Official user-facing
   releases should be signed and notarized.
6. Click `Pre-check` before the first real run.

The disk image also includes `README.txt` with a short responsible-use reminder
for users who open the package before reading the project documentation.
Release builds are checked with `packaging/verify-macos-dmg-smoke.sh`, which
mounts the dmg, verifies the `Applications` shortcut, and runs the packaged app
smoke check from inside the disk image. They are also checked with
`packaging/verify-macos-install-smoke.sh`, which copies the app into a temporary
Applications folder and launches it from that installed location.

## Release Signing

Maintainers can sign and notarize the disk image after building:

```bash
APPLE_DEVELOPER_ID_APPLICATION="Developer ID Application: Name (TEAMID)" \
APPLE_ID="name@example.com" \
APPLE_TEAM_ID="TEAMID" \
APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
./packaging/sign-notarize-macos.sh
```

The script signs the `.app` with hardened runtime, creates a signed dmg, submits
it to Apple notarization, staples the ticket, and validates the final dmg.

## Permissions

macOS may ask for access to Documents, Desktop, Downloads, removable drives, or
network folders. Grant access only to locations that contain documents and
images you are authorized to modify.

## Uninstall

Move `ImageInpaint.app` to Trash, then optionally delete:

```text
~/Library/Application Support/image-inpaint
~/Documents/Image Inpaint/Outputs
```

The app writes model cache and outputs outside the repository and does not edit
original documents in place.
