# Contributing

Thanks for taking a look at image-inpaint.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
python -m pytest -q
```

Install `.[iopaint]` only when you need to verify real model execution.

## Pull Request Checklist

- Keep source documents, processed outputs, downloaded images, model weights,
  and runtime folders out of the repository.
- Add or update tests for behavior changes.
- Run `python -m pytest -q`.
- Keep changes focused and avoid unrelated refactors.
- Document new CLI flags or config fields in `README.md`.

## Responsible Use

Do not contribute examples, fixtures, or documentation that show removing
third-party watermarks, signatures, notices, copyright labels, provenance marks,
or attribution without permission. Use tiny synthetic fixtures or clearly
authorized assets.
