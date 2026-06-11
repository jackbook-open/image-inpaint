# Windows Guide

Supported target: Windows 10 or Windows 11.

## Install and Launch

1. Download the Windows package.
2. For the simplest install, double-click `ImageInpaint-Setup-x64.exe`.
3. Follow the installer prompts.
4. Use the new desktop or Start menu shortcut to open `Image Inpaint`.
5. Click `Pre-check` before the first real run.

The recommended normal-user package is `ImageInpaint-Setup-x64.exe`. It installs
the app for the current Windows account, creates shortcuts, and registers a
normal uninstall entry without requiring Python or command-line setup.

The repository also provides `ImageInpaint-Windows-x64.zip` for portable-style
or advanced use. If you use the zip, right-click it, choose `Extract All`, open
`README-FIRST.txt`, and either run `ImageInpaint.exe` directly or double-click
`Install Image Inpaint.cmd` to use the script-based per-user installer.

Release checks install the setup exe into a temporary folder, launch the
installed smoke executable, and silently uninstall it before publishing. Zip
checks still verify the portable package layout.

## Security Software

Unsigned desktop builds can be scanned or blocked by antivirus tools. If Windows
shows a warning, confirm that the package came from the official project release
before allowing it. Production releases should be signed to reduce warnings.

## Uninstall

Open `Uninstall Image Inpaint` from the Start menu or Windows Settings. If you
installed from the zip script, you can also double-click `Uninstall Image
Inpaint.cmd` from the extracted package folder. The uninstaller removes the
installed app files, shortcuts, and current-user uninstall entry.

It intentionally keeps user output and cache folders. Delete these manually only
if you no longer need them:

```text
%LOCALAPPDATA%\image-inpaint
Documents\Image Inpaint\Outputs
```

The app does not store model cache or generated outputs inside the source
repository.
