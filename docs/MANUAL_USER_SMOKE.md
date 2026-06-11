# Manual User Smoke Checklist

Use this checklist with a tester who has not built the project and does not use
Python or the command line. Record the results in a release-specific copy of
`docs/RELEASE_EVIDENCE_TEMPLATE.md`.

Do not use private or third-party copyrighted material for this smoke. Use the
bundled example document or a small document and images that the tester is
authorized to modify.

## Tester Rules

- Start from the downloadable package, not the source checkout.
- Do not install Python, PyTorch, IOPaint, or project dependencies.
- Do not open a terminal.
- Time the flow from the moment the package is available on disk until the app
  first opens.
- Stop and record the exact message if security software, Gatekeeper, disk
  space, permissions, or runtime checks block the flow.

## Windows Smoke

Tester:

Windows version:

Package filename:

Checksum verified by release owner:

1. Download or receive `ImageInpaint-Windows-x64.zip`.
2. Extract the zip to a normal user folder such as Downloads or Desktop.
3. Open the extracted `ImageInpaint` folder.
4. Open `README-FIRST.txt` and confirm the responsible-use warning is visible.
5. Double-click `ImageInpaint.exe`.
6. Record time to first app window. Target: five minutes or less.
7. Confirm the app runs a startup runtime check and shows the model cache
   location or runtime status in the log.
8. Choose a Markdown document.
9. Confirm the output folder defaults to a safe user folder.
10. Choose a mask folder or choose a fallback area.
11. Click `Pre-check`.
12. Confirm the image list shows ready, skipped, or issue rows with readable
    reasons.
13. Select one image row and click `Skip selected`, then click `Clear skips`.
14. Click `Start processing`.
15. Confirm progress shows the current stage or current image and success,
    skipped, and failed counts.
16. Confirm the run finishes without modifying the original Markdown or images.
17. Click `Open output`.
18. Click `Open result document`.
19. Click `View log`.
20. Record any confusing wording, blocked action, antivirus warning, or missing
    output.

Optional install smoke:

1. Double-click `Install Image Inpaint.cmd`.
2. Confirm a desktop shortcut and Start menu entry appear.
3. Launch from the shortcut.
4. Run `Uninstall Image Inpaint.cmd`.
5. Confirm user outputs and model cache are not deleted by uninstall.

## macOS Apple Silicon Smoke

Tester:

macOS version:

Package filename:

Checksum verified by release owner:

1. Download or receive the Apple Silicon macOS dmg.
2. Open the dmg.
3. Confirm `ImageInpaint.app`, the Applications shortcut, and `README.txt` are
   visible.
4. Open `README.txt` and confirm the responsible-use warning is visible.
5. Drag `ImageInpaint.app` to Applications.
6. Open `Image Inpaint` from Applications.
7. Record time from opening the dmg to first app window. Target: five minutes or
   less.
8. Record the Gatekeeper result. Official public releases should open as a
   signed and notarized app.
9. Confirm the app runs a startup runtime check and shows the model cache
   location or runtime status in the log.
10. Run the same GUI workflow steps from the Windows smoke: choose Markdown,
    choose mask or fallback area, run `Pre-check`, skip/clear a selected image,
    start processing, then open output, result document, and log.
11. Record any permission prompt, Gatekeeper warning, confusing wording, blocked
    action, or missing output.

## macOS Intel Smoke

Repeat the macOS Apple Silicon smoke on an Intel Mac using the Intel macOS dmg.
Record the same fields and confirm the app launches without Rosetta-specific or
architecture-specific errors.

## Error Message Spot Checks

Run these only with disposable test files:

- Markdown references a missing local image: app should say the image is
  missing, not crash.
- Markdown references a remote image: app should skip it with a clear reason.
- Mask folder is missing a required mask and fallback area is `none`: app should
  show a readable issue.
- Mask dimensions do not match the source image: app should show a readable
  issue.
- Output folder is not writable: app should show a permission message.
- Runtime/model is unavailable or cache space is too low: app should show a
  short runtime message and keep details in the log.

## Pass Criteria

- The tester opens the app within five minutes without Python, terminal, or
  dependency installation.
- The tester completes the GUI workflow without modifying original files.
- The output folder contains `document.md`, `images/`, `backups/original.md`,
  `backups/images/`, and `logs/run.log`.
- The tester can open the output folder, result document, and log from the app.
- Error messages are understandable without reading a terminal.
- Responsible-use language is visible in the package and app flow.
