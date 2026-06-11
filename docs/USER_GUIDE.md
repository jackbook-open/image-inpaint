# Image Inpaint User Guide

Image Inpaint helps you process local images referenced by a Markdown document
and writes a new document that points to the processed copies. It does not
modify your original Markdown file or original images.

Use it only for documents and images you own or are authorized to modify. Do not
use it to remove third-party watermarks, copyright notices, signatures,
attribution, source marks, or protected content unless you have permission.

## Start the App

Windows users should download `ImageInpaint-Setup-x64.exe`, install it, then
open `Image Inpaint` from the desktop or Start menu shortcut. A zip package is
also available for portable-style use.

macOS users should download the macOS package, open `ImageInpaint.app`, and move
it to Applications if desired.

On first launch, the app automatically checks that the bundled runtime, model
cache folder, free cache disk space, and required image libraries are available.
If the real inpainting runtime is not ready, the app shows a short message and
keeps the technical details in the log area. Use `Check runtime` to rerun that
check after fixing a problem. After choosing a document, `Pre-check` also runs
the same runtime check while scanning your document and showing which images
would be processed. `Start processing` will wait until runtime problems are
fixed.

## Process a Document

1. Choose a Markdown document.
2. Confirm or change the output folder. The default is a new timestamped folder
   under your Documents folder.
3. Choose a mask folder if you already have masks with the same filenames as
   your source images.
4. Choose a fallback area only when you want the app to generate simple masks for
   images without matching mask files.
5. Click `Pre-check` to fill the image list with items that are ready, skipped,
   missing, waiting for masks, using a fallback area, or blocked by a mismatched
   mask size. Pre-check does not write output files, and the status line will
   show how many images are ready, skipped, or have issues.
6. Select any image rows you do not want to process and click `Skip selected`.
   Use `Clear skips` if you change your mind, then run `Pre-check` again to
   refresh the list.
7. Click `Start processing`. Use `Cancel` if you need to stop a long run.
8. When the run finishes, use `Open output`, `Open result document`, or `View
   log`.

The image list is the main place to review what the app found in your document.
The status line and progress bar show the current stage and the success,
skipped, and failed counts. During a run, the status line also shows the image
currently being prepared or processed when that information is available. The
log keeps the detailed technical trace for troubleshooting. During long
processing or first-run model preparation, recent runtime messages may appear in
the status line so you can tell the app is still working.

Advanced settings are hidden by default. Leave them closed unless a developer or
support note asks you to change the processing device or cache location.

## Output Folder

Each real run writes a separate folder:

```text
output-folder/
  document.md
  images/
  backups/
    original.md
    images/
  logs/
    run.log
```

The result document points to files under `images/`. Backups are copies for
review and recovery; they are not edited in place.

If the selected output folder already contains files, the app automatically uses
a new numbered folder next to it, such as `MyOutput-1`, so existing results are
not overwritten.

## Maintenance

`Check runtime` reruns the environment check without requiring a document. The
same check runs automatically shortly after the app opens. Use it manually after
installing a new package, clearing the cache, changing security settings, or
fixing a runtime error.

`Clear cache` removes the local model cache folder and recreates it empty. Use it
when a model download was interrupted or the app reports a damaged cache.

`Reset defaults` restores the recommended output folder and processing defaults
while keeping the selected Markdown document.

When a run is cancelled, the app stops the current processing command, keeps the
original files untouched, and writes a log for troubleshooting. A cancelled run
does not write a result Markdown document.

If startup fails, check disk space, file permissions, and whether your security
software blocked the app. The log view contains details that are useful when
reporting an issue.
