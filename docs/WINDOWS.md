# Windows Guide

Supported target: Windows 10 or Windows 11.

## Install and Launch

1. Download the Windows package.
2. If it is a zip package, right-click it, choose `Extract All`, and extract it
   to a normal folder such as Downloads or Documents.
3. Open `README-FIRST.txt` if you want the shortest package-level checklist.
4. Double-click `Install Image Inpaint.cmd`.
5. Use the new desktop or Start menu shortcut to open `Image Inpaint`.
6. Click `Pre-check` before the first real run.

The current repository provides a PyInstaller `onedir` build and a release zip
at `release\ImageInpaint-Windows-x64.zip`. The zip includes a per-user installer
that copies the app to `%LOCALAPPDATA%\ImageInpaint\app`, creates desktop and
Start menu shortcuts, and registers a normal uninstall entry for the current
Windows account. Users can also run `ImageInpaint.exe` directly from the
extracted folder if they prefer a portable-style launch.

Release checks install the app into temporary user folders and launch the
installed copy before publishing, so the desktop and Start menu shortcuts point
to the same executable that was smoke-tested.

## Security Software

Unsigned desktop builds can be scanned or blocked by antivirus tools. If Windows
shows a warning, confirm that the package came from the official project release
before allowing it. Production releases should be signed to reduce warnings.

## Uninstall

Open `Uninstall Image Inpaint` from the Start menu, or double-click
`Uninstall Image Inpaint.cmd` from the extracted package folder. The uninstaller
removes the installed app files, shortcuts, and current-user uninstall entry.

It intentionally keeps user output and cache folders. Delete these manually only
if you no longer need them:

```text
%LOCALAPPDATA%\image-inpaint
Documents\Image Inpaint\Outputs
```

The app does not store model cache or generated outputs inside the source
repository.
