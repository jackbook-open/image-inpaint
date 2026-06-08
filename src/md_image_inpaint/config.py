from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import RunConfig


CONFIG_KEYS = {
    "out_dir",
    "mask_dir",
    "region",
    "engine",
    "device",
    "model",
    "model_dir",
    "dry_run",
    "verbose",
    "iopaint_cmd",
    "skip_patterns",
}


def load_config_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config file must contain a YAML mapping")
    unknown = sorted(set(data) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f"unknown config option(s): {', '.join(unknown)}")
    return data


def merge_config(
    markdown_path: Path,
    cli_values: dict[str, Any],
    config_path: Path | None = None,
) -> RunConfig:
    file_values = load_config_file(config_path)
    merged = {**file_values}
    for key, value in cli_values.items():
        if value is not None:
            merged[key] = value

    out_dir_value = merged.get("out_dir") or merged.get("out") or "output"
    mask_dir_value = merged.get("mask_dir")
    model_dir_value = merged.get("model_dir")
    return RunConfig(
        markdown_path=markdown_path,
        out_dir=Path(out_dir_value),
        mask_dir=Path(mask_dir_value) if mask_dir_value else None,
        region=merged.get("region"),
        engine=merged.get("engine", "iopaint"),
        device=merged.get("device", "cpu"),
        model=merged.get("model", "lama"),
        model_dir=Path(model_dir_value) if model_dir_value else None,
        dry_run=bool(merged.get("dry_run", False)),
        verbose=bool(merged.get("verbose", False)),
        iopaint_cmd=merged.get("iopaint_cmd", "iopaint"),
        skip_patterns=_normalize_skip_patterns(merged.get("skip_patterns")),
    )


def _normalize_skip_patterns(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("skip_patterns must be a list of strings")
    return value
