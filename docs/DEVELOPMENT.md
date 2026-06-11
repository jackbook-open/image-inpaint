# Development and Packaging

## Local Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
python -m pytest -q
```

Start the desktop app from source:

```powershell
python -m md_image_inpaint --gui
```

Install real inpainting support only when needed:

```powershell
python -m pip install -e .[iopaint]
```

## Windows Package

Use Python 3.12 for release builds when possible. IOPaint/PyTorch wheels may lag
behind the newest Python versions.

```powershell
.\packaging\build-windows.ps1
```

For a lightweight GUI smoke package without IOPaint:

```powershell
.\packaging\build-windows.ps1 -NoIopaint
```

To bundle a prepared IOPaint/PyTorch runtime directory:

```powershell
.\packaging\prepare-iopaint-runtime-windows.ps1 -RuntimeDir iopaint-runtime -PythonCommand C:\Python312\python.exe
.\packaging\build-windows.ps1 -RuntimeDir C:\path\to\iopaint-runtime
```

To also build the normal-user `.exe` installer, install Inno Setup 6 and add
`-Installer`:

```powershell
.\packaging\build-windows.ps1 -RuntimeDir C:\path\to\iopaint-runtime -Installer
```

If `ISCC.exe` is not on `PATH`, pass it explicitly:

```powershell
.\packaging\build-windows.ps1 -RuntimeDir C:\path\to\iopaint-runtime -Installer -InnoSetupCompiler "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

The runtime preparation script checks for 64-bit Python 3.10, 3.11, or 3.12
before creating the runtime. If the host only has Python 3.13 or a 32-bit Python,
the script stops before downloading large dependencies and asks for a compatible
`-PythonCommand`.

When `-RuntimeDir` is supplied, the build venv installs only the desktop
dependencies and copies the prepared runtime into the package. The packaged
smoke check still requires that the copied runtime exposes an `iopaint` command.
Native command failures from pip, PyInstaller, or the smoke check stop the build.

The build runs a packaged `--smoke-check`, writes
`dist\ImageInpaint\ImageInpaint.exe`, and creates
`release\ImageInpaint-Windows-x64.zip` plus
`release\ImageInpaint-Windows-x64.zip.sha256`.
When `-Installer` is supplied, it also creates
`release\ImageInpaint-Setup-x64.exe` plus
`release\ImageInpaint-Setup-x64.exe.sha256`.
It also runs `packaging\verify-windows-install-smoke.ps1`, which installs and
uninstalls the packaged app inside temporary user folders and a test registry
key so the normal desktop shortcut, Start menu shortcut, and uninstall entry are
verified without touching the real user install location.
Real-runtime builds run this check with `-LaunchSmoke -RequireIopaint`, so the
installed copy under the temporary user profile must also start and find the
bundled IOPaint runtime.
After creating the zip, the build runs `packaging\verify-windows-zip-smoke.ps1`
to inspect the exact download artifact and confirm that the executable,
installer scripts, README, and runtime entrypoint are present. For lightweight
packages or manual checks, add `-FullExtract` to extract the zip, run the bundled
smoke executable, and install/uninstall from the extracted package directory.
Full extraction mode also launches the installed smoke executable with
`--require-iopaint`.
The zip smoke also verifies the `.sha256` sidecar with
`python packaging/verify-checksum.py`.

Installer builds run `packaging\verify-windows-installer-smoke.ps1`, which
silently installs the setup exe to a scratch directory, runs
`ImageInpaintSmoke.exe`, and silently uninstalls it. Real-runtime installer
builds run that smoke with `-RequireIopaint`.

Windows builds also include `ImageInpaintSmoke.exe`, a console-mode copy of the
same desktop entrypoint used only by packaging scripts. Release checks use it so
PowerShell can observe reliable stdout, stderr, and exit codes while normal
users continue launching the windowed `ImageInpaint.exe`.

To prove the packaged Windows app can execute the full processing workflow
without downloading IOPaint or model weights, run the fake-runtime smoke:

```powershell
.\packaging\verify-packaged-process-smoke.ps1
```

This creates a tiny local `iopaint` stand-in, runs the packaged
`--process-smoke`, verifies output Markdown, processed images, backups, log
files, and unchanged source files, then removes the smoke output. It does not
prove real ML inpainting quality.

## macOS Package

Use Python 3.12 for release builds when possible. Build separate artifacts on
Apple Silicon and Intel hosts if you need native packages for both architectures.
Keep macOS packaging scripts compatible with the system `/bin/bash` 3.2 and BSD
userland tools. Avoid Bash 4-only helpers such as `mapfile`, associative arrays,
and case-conversion parameter expansion, and avoid GNU-only flags such as
`realpath`, `grep -P`, or `sed -r`.

```bash
chmod +x packaging/build-macos.sh
./packaging/build-macos.sh
```

For a lightweight GUI smoke package without IOPaint:

```bash
./packaging/build-macos.sh --no-iopaint
```

To bundle a prepared IOPaint/PyTorch runtime directory:

```bash
./packaging/prepare-iopaint-runtime-macos.sh --runtime-dir=iopaint-runtime --python=/path/to/python3.12
./packaging/build-macos.sh --runtime-dir=/path/to/iopaint-runtime
```

The runtime preparation script checks for 64-bit Python 3.10, 3.11, or 3.12
before creating the runtime. If the host only has Python 3.13 or an incompatible
architecture, the script stops before downloading large dependencies and asks
for a compatible `--python` value.

When `--runtime-dir` is supplied, the build venv installs only the desktop
dependencies and copies the prepared runtime into the `.app`. The packaged
smoke check still requires that the copied runtime exposes an `iopaint` command.

The build runs a packaged `--smoke-check`, writes `dist/ImageInpaint.app`, and
creates `release/ImageInpaint-macOS.dmg` on macOS. The GitHub Actions package
matrix runs this on Apple Silicon and Intel hosted runners and uploads separate
`ImageInpaint-macOS-arm64` and `ImageInpaint-macOS-intel` artifacts.
The build also writes `release/ImageInpaint-macOS.dmg.sha256`, and CI uploads it
with the dmg.

macOS builds also include `ImageInpaintSmoke` where PyInstaller exposes it in the
bundle or onedir output. Packaging and release scripts prefer that executable for
automation, then fall back to the main app executable if needed.

After building a dmg on macOS, run:

```bash
./packaging/verify-macos-dmg-smoke.sh
./packaging/verify-macos-install-smoke.sh
```

This verifies the disk image, mounts it at a temporary mount point, checks that
`ImageInpaint.app`, the `/Applications` shortcut, and `README.txt` are present,
and runs the packaged smoke check from inside the mounted image. The install
smoke copies the app into a temporary `Applications` folder and launches it from
that installed location, without writing to the real `/Applications` directory.
Both macOS smoke scripts verify the `.sha256` sidecar before mounting.

To prove the packaged macOS app can execute the full processing workflow without
downloading IOPaint or model weights, run:

```bash
./packaging/verify-packaged-process-smoke.sh
```

This uses a tiny local `iopaint` stand-in and the packaged `--process-smoke`.
It proves packaged path handling, subprocess invocation, document rewriting,
backups, logs, and source-file safety. It does not prove real ML inpainting
quality.

## Packaging Notes

The desktop app uses PyInstaller `onedir` builds. This is friendlier for large
ML dependencies than a single self-extracting executable and is easier to inspect
when support issues occur.

Current engine integration calls an `iopaint` command. Release builds that claim
one-click processing must verify that the packaged runtime provides that command
inside the app environment, or replace the engine adapter with an embedded
library call. Do not ship model weights in the repository; use the app model
cache path and document the first-run download behavior.

The desktop runtime resolver looks for IOPaint in this order:

1. `IMAGE_INPAINT_RUNTIME_DIR`
2. `runtime/` or `iopaint-runtime/` next to the packaged executable
3. the packaged executable directory
4. the system `PATH`

Use this to keep PyTorch, IOPaint, and related heavy runtime files outside the
source tree while still making a release package self-contained for normal
users.

The runtime directory should contain an executable `iopaint` command at its root,
under `bin/` on macOS, or under `Scripts/` on Windows. The build scripts copy it
into the packaged app as `runtime/`.

## Release Smoke Checks

Run these checks before publishing a package:

```powershell
python -m pytest -q
.\packaging\build-windows.ps1 -NoIopaint
dist\ImageInpaint\ImageInpaint.exe --smoke-check
.\packaging\verify-packaged-process-smoke.ps1
.\packaging\verify-windows-install-smoke.ps1
.\packaging\verify-windows-zip-smoke.ps1
```

To include the lightweight setup exe in this local smoke, install Inno Setup and
run:

```powershell
.\packaging\build-windows.ps1 -NoIopaint -Installer
.\packaging\verify-windows-installer-smoke.ps1
```

On macOS:

```bash
python -m pytest -q
./packaging/build-macos.sh --no-iopaint
dist/ImageInpaint/ImageInpaint --smoke-check
./packaging/verify-packaged-process-smoke.sh
./packaging/verify-macos-dmg-smoke.sh
```

For real processing packages, use the release verification scripts below. They
call the packaged executable itself with a hidden `--process-smoke` command so
the evidence proves the distributed app can run the example workflow, not just
the source checkout. Release scripts prefer the `ImageInpaintSmoke` executable
for reliable automation output and exit codes.

Windows real-processing release verification:

```powershell
.\packaging\verify-release-windows.ps1
.\packaging\verify-windows-zip-smoke.ps1
.\packaging\verify-windows-installer-smoke.ps1 -RequireIopaint
```

Use `.\packaging\verify-windows-zip-smoke.ps1 -FullExtract` for an additional
full extraction and installed-app launch check when artifact size and CI time
allow.

macOS real-processing release verification:

```bash
./packaging/verify-release-macos.sh
./packaging/verify-macos-dmg-smoke.sh --require-iopaint
./packaging/verify-macos-install-smoke.sh --require-iopaint
```

## Continuous Packaging

The `Desktop package` GitHub Actions workflow runs tests, builds the lightweight
Windows setup exe and zip plus separate Apple Silicon and Intel macOS dmg
packages without IOPaint, runs each packaged `--smoke-check`, runs each packaged
app through the fake-runtime processing smoke, verifies the Windows setup exe
with a silent install/uninstall smoke, verifies the macOS dmg installer layout,
verifies that the app can be copied to and launched from a temporary
Applications folder, and uploads the packages as workflow artifacts.

The macOS matrix intentionally uses `macos-15` for Apple Silicon and
`macos-15-intel` for Intel. Do not collapse these to `macos-latest` unless the
release checklist is updated with equivalent evidence for both architectures.

These artifacts prove that the desktop shell, bundled Python runtime, Tkinter,
Pillow, PyYAML, platform packaging scripts, release archive creation, packaged
subprocess invocation, output layout, backups, logs, and source-file safety work
on hosted Windows and macOS runners. They do not prove real inpainting until a
release job installs or embeds IOPaint/PyTorch and runs
`verify-release-windows.ps1` or `verify-release-macos.sh`.

For release candidates, run the manually triggered `Desktop real runtime
release` workflow. It prepares IOPaint/PyTorch runtimes on Windows and macOS,
builds packages with those runtimes embedded, runs the real release verifiers,
verifies each real-runtime macOS dmg with `--require-iopaint`, and uploads
`ImageInpaint-Windows-x64-real-runtime`,
`ImageInpaint-macOS-arm64-real-runtime`, and
`ImageInpaint-macOS-intel-real-runtime` artifacts. Expect this workflow to take
longer and produce much larger artifacts than the lightweight packaging
workflow.

Before publishing, copy `docs/RELEASE_EVIDENCE_TEMPLATE.md` for the candidate
and fill in the workflow URLs, artifact links, command results, notarization
result, and manual user-smoke notes. Do not store large artifacts, model caches,
runtime folders, private documents, or processed user outputs in the repository.

For macOS public releases, set `notarize_macos` to `true` when dispatching that
workflow and configure these repository secrets:

```text
APPLE_DEVELOPER_ID_APPLICATION
APPLE_ID
APPLE_TEAM_ID
APPLE_APP_SPECIFIC_PASSWORD
```

Alternatively, provide `APPLE_NOTARY_KEYCHAIN_PROFILE` on a self-hosted macOS
runner. The workflow runs `packaging/sign-notarize-macos.sh`, which signs the
app with hardened runtime, submits the dmg through `xcrun notarytool`, staples
the notarization ticket, and uploads the notarized dmg.
