# Troubleshooting

## The App Shows a Short Error Message

The status line shows a short user-readable summary, such as a missing file,
permission problem, or low disk space. The log area keeps the technical detail
needed for support. After fixing the issue, run `Pre-check` again before
starting a real processing run.

## Pre-check Says the Runtime Is Not Ready

Use the details in the log area to see what is missing. A normal user package
should include the needed Python runtime and libraries. Developer builds may need
`python -m pip install -e .[iopaint]`.

The app runs this check automatically shortly after startup. Click
`Check runtime` after fixing the issue to rerun the environment check without
selecting a document. Pre-check may still list document images so you can review
missing files, masks, and skipped items. Real processing will not start until
the runtime check passes.

## Model Download Fails

Check the network connection and free disk space. Click `Clear cache`, then run
`Check runtime` or `Pre-check` again. The cache location and available cache
disk space are shown in the log. Keep at least 2 GB free for first-run model
preparation.

## Processing Is Slow

CPU processing can be slow. Use smaller batches first, close other heavy apps,
and prefer masks that cover only the area that needs repair.

During long processing or first-run model preparation, the status line and log
may show recent runtime messages. If those messages continue to change, the app
is still working.

## Images Are Skipped

The app skips remote images, missing files, unsupported formats, mismatched
masks, and images without a matching mask when no fallback area is selected. Run
`Pre-check` to see the exact reason for each image.

Supported source image formats are PNG, JPEG, WebP, and BMP. Animated GIF and SVG
files are skipped in this release.

Mask images must have the same width and height as the source image. If the size
does not match, create a new mask from the same source image or choose a fallback
area.

## Output Is Empty

Open `logs/run.log` in the output folder. If every image was skipped, check that
the Markdown paths point to local files and that mask filenames match the source
image filenames.

## Permission Errors

Move the document and images to a normal user folder such as Documents. On macOS,
grant access when the system prompts for it.

## Paths with Spaces or Chinese Characters

The app is designed to handle spaces and non-ASCII paths. If a packaged runtime
or model tool fails on such a path, copy the document to a shorter folder and
keep the original files unchanged while reporting the issue with `logs/run.log`.
