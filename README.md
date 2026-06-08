# image-inpaint

Batch inpaint local images referenced by documents. The first supported document
type is Markdown; the project is named `image-inpaint` so support for other file
formats can be added later.

The tool scans document image references, skips remote or missing images with
clear logs, applies masks to authorized local images, runs IOPaint/LaMa in batch
mode, and writes a new document copy that points at the processed images.

## Responsible Use

Use this tool only on documents and images that you own or are explicitly
authorized to modify. Do not use it to remove third-party watermarks, signatures,
notices, provenance marks, copyright labels, or attribution unless you have the
legal right and permission to do so.

This repository intentionally does not include real-world user documents,
processed case outputs, model weights, runtime environments, downloaded remote
images, or large caches.

## Features

- Parse Markdown image syntax such as `![alt](path)`.
- Resolve relative and absolute local image paths.
- Skip remote URLs and missing local files with explicit reasons.
- Match masks by original image filename.
- Generate simple fixed-region masks when no mask file is provided.
- Run IOPaint/LaMa through `iopaint run`.
- Keep the source document and source images unchanged.
- Write backups, processed images, and a rewritten output document.
- Provide a CLI and a small Tkinter GUI.

## Installation

Python 3.10+ is required. IOPaint has heavier dependencies, including PyTorch,
so a Python version supported by your IOPaint/PyTorch build is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Install IOPaint support when you are ready to run real inpainting:

```powershell
python -m pip install -e .[iopaint]
iopaint --help
```

## Quick Start

Dry-run the bundled tiny example:

```powershell
python -m md_image_inpaint examples\document.md --out output --mask-dir examples\masks --dry-run --verbose
```

Run real batch inpainting with IOPaint/LaMa:

```powershell
python -m md_image_inpaint examples\document.md --out output --mask-dir examples\masks --engine iopaint --model lama --device cpu --model-dir ..\.model-cache --verbose
```

The console script is also installed as:

```powershell
image-inpaint examples\document.md --out output --mask-dir examples\masks --dry-run
```

## GUI

```powershell
python -m md_image_inpaint --gui
```

The GUI writes the same output layout as the CLI and shows the run log in the
window.

## Output Layout

For `--out output`, the tool writes:

```text
output/
  document.md
  images/
  backups/
    original.md
    images/
```

The source document and source images are not modified in place.

## Masks

Mask files are white where pixels should be inpainted and black where pixels
should be preserved.

When `--mask-dir` is provided, masks are matched by original image filename:

```text
document-images/screenshot.png
masks/screenshot.png
```

When no matching mask is found, `--region` can generate a simple fixed mask:

- `top-left`
- `top-right`
- `bottom-left`
- `bottom-right`
- `bottom-strip`
- `none`

## Config File

```yaml
out_dir: output
mask_dir: examples/masks
engine: iopaint
model: lama
model_dir: ../.model-cache
device: cpu
region: none
dry_run: false
verbose: true
skip_patterns:
  - "*.gif"
```

Run with:

```powershell
python -m md_image_inpaint examples\document.md --config examples\config.yaml
```

Command-line values override config file values. `model_dir` is passed to
IOPaint as `--model-dir`, so model downloads can stay outside this repository.

## Development

```powershell
python -m pip install -e .[dev]
python -m pytest -q
```

The test suite uses tiny generated images and a fake IOPaint command; it does
not download model weights.

## Current Limitations

- Markdown is the only supported document format today.
- Remote images are skipped. Download remote images yourself only when you have
  the rights to modify them, then reference those local files from Markdown.
- Markdown parsing targets common `![alt](path)` syntax.
- Inpainting quality depends on the mask, source image, and selected model.

## Repository Hygiene

Do not commit:

- `output/`, `outputs/`, or processed user documents.
- model weights, checkpoints, or caches.
- local runtimes such as `.runtime/` or `.venv/`.
- real customer/user images, screenshots, or logs.

## License

MIT. See [LICENSE](LICENSE).
