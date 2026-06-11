# Release Checklist

Use this checklist before calling a desktop release ready for normal users.
For each release candidate, copy `docs/RELEASE_EVIDENCE_TEMPLATE.md` and fill
the commands, workflow URLs, artifact links, user-smoke notes, and signing
results before publishing.
Use `docs/ACCEPTANCE_MATRIX.md` to map each product requirement to the required
evidence before marking the release ready.
Use `docs/MANUAL_USER_SMOKE.md` for the non-developer Windows and macOS user
smoke steps.

## Required Automated Evidence

- `python -m pytest -q` passes.
- `python packaging/verify-repository-boundaries.py` passes.
- `python packaging/verify-checksum.py <artifact>` passes for every uploaded
  setup exe, zip, or dmg.
- Release hosts have 64-bit Python 3.10, 3.11, or 3.12 available for preparing
  IOPaint/PyTorch runtimes.
- Runtime preparation scripts complete on release hosts:
  - `packaging\prepare-iopaint-runtime-windows.ps1`
  - `packaging/prepare-iopaint-runtime-macos.sh`
- GitHub Actions `Desktop package` passes on Windows and macOS.
- Windows artifact `ImageInpaint-Setup-x64.exe` is uploaded.
- Windows artifact `ImageInpaint-Setup-x64.exe.sha256` is uploaded.
- Windows artifact `ImageInpaint-Windows-x64.zip` is uploaded.
- Windows artifact `ImageInpaint-Windows-x64.zip.sha256` is uploaded.
- macOS artifacts are uploaded for both Apple Silicon and Intel:
  `ImageInpaint-macOS-arm64` and `ImageInpaint-macOS-intel`.
- macOS `.dmg.sha256` checksum files are uploaded with each macOS artifact.
- Packaged `--smoke-check` passes on each platform.
- Windows package passes `packaging\verify-windows-install-smoke.ps1`.
- Real-runtime Windows package passes
  `packaging\verify-windows-install-smoke.ps1 -PackageDir dist\ImageInpaint
  -LaunchSmoke -RequireIopaint`, proving the installed copy can start.
- Windows setup artifact passes `packaging\verify-windows-installer-smoke.ps1`.
- Real-runtime Windows setup artifact passes
  `packaging\verify-windows-installer-smoke.ps1 -RequireIopaint`.
- Windows downloaded zip artifact passes `packaging\verify-windows-zip-smoke.ps1`.
- Windows downloaded zip artifact passes
  `packaging\verify-windows-zip-smoke.ps1 -FullExtract` when release time and
  artifact size allow.
- macOS dmg passes `packaging/verify-macos-dmg-smoke.sh`.
- macOS app passes `packaging/verify-macos-install-smoke.sh` after being copied
  from the dmg into a temporary Applications folder.
- Real-runtime macOS dmg passes
  `packaging/verify-macos-dmg-smoke.sh --require-iopaint`.
- Real-runtime macOS installed app passes
  `packaging/verify-macos-install-smoke.sh --require-iopaint`.
- Packaged fake-runtime processing smoke passes on each platform:
  - `packaging\verify-packaged-process-smoke.ps1`
  - `packaging/verify-packaged-process-smoke.sh`
- Manual GitHub Actions `Desktop real runtime release` passes before publishing
  a real user-facing release.
- Public macOS release has `notarize_macos` enabled or an equivalent local
  `packaging/sign-notarize-macos.sh` run, and the final dmg has a stapled
  notarization ticket.
- Real-processing packages are built with a prepared `runtime/` directory or an
  equivalent embedded IOPaint/PyTorch runtime.

## Required Real-Processing Evidence

- Windows build with IOPaint/PyTorch available passes
  `packaging\verify-release-windows.ps1`.
- macOS build with IOPaint/PyTorch available passes
  `packaging/verify-release-macos.sh`.
- The example document produces:
  - `document.md`
  - processed image output
  - `backups/original.md`
  - `logs/run.log`
- Original example Markdown and image files remain unchanged.
- Fake-runtime processing smoke is not a substitute for this section; it proves
  packaging and file-safety behavior, not real IOPaint/PyTorch processing.

## Required Manual User Smoke

- A non-developer Windows user can run `ImageInpaint-Setup-x64.exe`, install the
  app, and open it from a shortcut.
- A non-developer macOS user can open the dmg/app and pass the first-run security
  prompts.
- The GUI can select a Markdown document, run `Pre-check`, start processing, and
  open the output folder, result document, and log.
- Error messages for missing masks, missing images, remote images, and missing
  model/runtime are understandable without reading terminal output.
- Results are recorded using `docs/MANUAL_USER_SMOKE.md` and copied into the
  release evidence file.

## Release Boundaries

Do not publish model weights, user documents, processed private output,
`.venv/`, `.runtime/`, `.model-cache/`, `dist/`, `build/`, or `release/` into
the source repository.
