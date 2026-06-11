# Release Evidence Template

Copy this file for each release candidate and fill it before publishing a
normal-user desktop release. Keep evidence links or logs outside the source
repository when they contain large artifacts, model caches, or user files.

## Release Candidate

- Version:
- Commit:
- Date:
- Release owner:
- Windows artifact:
- Windows artifact SHA256:
- macOS Apple Silicon artifact:
- macOS Apple Silicon artifact SHA256:
- macOS Intel artifact:
- macOS Intel artifact SHA256:
- Notarized macOS artifact:
- Notarized macOS artifact SHA256:

## Source Boundary Evidence

- `python packaging/verify-repository-boundaries.py`:
- Confirm no model weights, runtimes, caches, release archives, private
  documents, or processed user outputs are tracked:
- Confirm release artifacts are stored outside git or uploaded as CI artifacts:

## Automated Test Evidence

- `python -m pytest -q`:
- `Desktop package` workflow run URL:
- `Desktop real runtime release` workflow run URL:
- Windows real-runtime artifact uploaded:
- Windows real-runtime artifact checksum uploaded:
- macOS Apple Silicon real-runtime artifact uploaded:
- macOS Apple Silicon real-runtime artifact checksum uploaded:
- macOS Intel real-runtime artifact uploaded:
- macOS Intel real-runtime artifact checksum uploaded:

## Windows Evidence

- Build host:
- Python used for IOPaint runtime:
- Runtime preparation command and result:
- Build command and result:
- `packaging\verify-release-windows.ps1` result:
- `packaging\verify-windows-zip-smoke.ps1` result:
- `packaging\verify-windows-zip-smoke.ps1 -FullExtract` result:
- Manual smoke checklist used: `docs/MANUAL_USER_SMOKE.md`
- Non-developer user smoke tester:
- Windows version:
- Time from download/extract to first app window:
- Opened without Python, terminal, or dependency installation:
- GUI workflow result:
  - Select Markdown:
  - Run `Pre-check`:
  - Select mask or fallback region:
  - Start processing:
  - Open output folder:
  - Open result document:
  - Open log:
- Optional install/uninstall smoke result:
- Error-message spot checks:
  - Missing image:
  - Remote image:
  - Missing mask or region:
  - Missing model/runtime:

## macOS Apple Silicon Evidence

- Build host:
- macOS version:
- Python used for IOPaint runtime:
- Runtime preparation command and result:
- Build command and result:
- `packaging/verify-release-macos.sh` result:
- `packaging/verify-macos-dmg-smoke.sh --require-iopaint` result:
- `packaging/verify-macos-install-smoke.sh --require-iopaint` result:
- Manual smoke checklist used: `docs/MANUAL_USER_SMOKE.md`
- Non-developer user smoke tester:
- Time from download/open dmg to first app window:
- Gatekeeper result:
- Opened without Python, terminal, or dependency installation:
- GUI workflow result:

## macOS Intel Evidence

- Build host:
- macOS version:
- Python used for IOPaint runtime:
- Runtime preparation command and result:
- Build command and result:
- `packaging/verify-release-macos.sh` result:
- `packaging/verify-macos-dmg-smoke.sh --require-iopaint` result:
- `packaging/verify-macos-install-smoke.sh --require-iopaint` result:
- Manual smoke checklist used: `docs/MANUAL_USER_SMOKE.md`
- Non-developer user smoke tester:
- Time from download/open dmg to first app window:
- Gatekeeper result:
- Opened without Python, terminal, or dependency installation:
- GUI workflow result:

## macOS Signing And Notarization Evidence

- `notarize_macos=true` workflow run URL or local signing host:
- Developer ID Application identity:
- `packaging/sign-notarize-macos.sh` result:
- `xcrun stapler validate` result:
- `spctl --assess --type open` result:
- Notarized dmg path or artifact URL:
- Confirm the final public macOS artifact is the notarized dmg:

## File Safety Evidence

- Original Markdown unchanged:
- Original images unchanged:
- Output directory contains `document.md`:
- Output directory contains processed images:
- Output directory contains `backups/original.md`:
- Output directory contains `backups/images/`:
- Output directory contains `logs/run.log`:
- Processing failure behavior checked without corrupting existing output:

## Responsible-Use Evidence

- App package README contains responsible-use language:
- GUI shows responsible-use notice:
- User docs warn against unauthorized removal of protected content:
- Release notes include responsible-use reminder:

## Release Decision

- All automated checks passed:
- All Windows user-smoke checks passed:
- All macOS Apple Silicon user-smoke checks passed:
- All macOS Intel user-smoke checks passed:
- Public macOS artifact is signed and notarized:
- Known issues:
- Release approved by:
