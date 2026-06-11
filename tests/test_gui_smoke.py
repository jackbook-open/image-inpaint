from __future__ import annotations

import errno
import runpy
import sys
from pathlib import Path


def test_gui_entrypoint_imports() -> None:
    from md_image_inpaint import desktop_app, gui

    assert gui.App.__name__ == "App"
    assert desktop_app.main is gui.main


def test_desktop_smoke_check_runs_without_window(capsys) -> None:
    from md_image_inpaint.desktop_app import run

    exit_code = run(["--smoke-check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Desktop runtime check passed" in captured.out


def test_desktop_entrypoint_runs_as_script(capsys, monkeypatch) -> None:
    entrypoint = Path(__file__).parents[1] / "src" / "md_image_inpaint" / "desktop_app.py"
    monkeypatch.setattr(sys, "argv", [str(entrypoint), "--smoke-check"])

    try:
        runpy.run_path(str(entrypoint), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "Desktop runtime check passed" in captured.out


def test_process_smoke_requires_markdown_and_output(capsys) -> None:
    from md_image_inpaint.desktop_app import run

    exit_code = run(["--process-smoke"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--process-smoke requires --markdown and --out" in captured.err


def test_process_smoke_output_validation_accepts_complete_run(tmp_path: Path) -> None:
    from md_image_inpaint.desktop_app import _file_hash, _process_smoke_failures
    from md_image_inpaint.models import ImageTask, RunResult

    source_md = tmp_path / "source.md"
    source_image = tmp_path / "source.png"
    source_md.write_text("![sample](source.png)", encoding="utf-8")
    source_image.write_bytes(b"source image")
    out_dir = tmp_path / "output"
    output_images_dir = out_dir / "images"
    backup_images_dir = out_dir / "backups" / "images"
    log_dir = out_dir / "logs"
    output_images_dir.mkdir(parents=True)
    backup_images_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)
    output_markdown = out_dir / "document.md"
    output_image = output_images_dir / "0001-source.png"
    backup_image = backup_images_dir / "source.png"
    output_markdown.write_text("![sample](images/0001-source.png)", encoding="utf-8")
    output_image.write_bytes(b"processed image")
    (out_dir / "backups" / "original.md").write_text(source_md.read_text(encoding="utf-8"), encoding="utf-8")
    backup_image.write_bytes(source_image.read_bytes())
    log_path = log_dir / "run.log"
    log_path.write_text("Summary: processed=1, skipped=0, failed=0", encoding="utf-8")
    task = ImageTask(
        _ref("source.png"),
        True,
        "ready",
        output_path=output_image,
        backup_path=backup_image,
        success=True,
    )
    result = RunResult(
        markdown_path=source_md,
        output_markdown_path=output_markdown,
        output_images_dir=output_images_dir,
        log_path=log_path,
        tasks=[task],
        success_count=1,
    )

    failures = _process_smoke_failures(
        result,
        {
            source_md.resolve(): _file_hash(source_md),
            source_image.resolve(): _file_hash(source_image),
        },
    )

    assert failures == []


def test_process_smoke_output_validation_reports_missing_release_artifacts(tmp_path: Path) -> None:
    from md_image_inpaint.desktop_app import _file_hash, _process_smoke_failures
    from md_image_inpaint.models import ImageTask, RunResult

    source_md = tmp_path / "source.md"
    source_image = tmp_path / "source.png"
    source_md.write_text("![sample](source.png)", encoding="utf-8")
    source_image.write_bytes(b"source image")
    original_hashes = {
        source_md.resolve(): _file_hash(source_md),
        source_image.resolve(): _file_hash(source_image),
    }
    source_image.write_bytes(b"changed")
    out_dir = tmp_path / "output"
    output_images_dir = out_dir / "images"
    backup_images_dir = out_dir / "backups" / "images"
    output_images_dir.mkdir(parents=True)
    backup_images_dir.mkdir(parents=True)
    output_markdown = out_dir / "document.md"
    output_markdown.write_text("![sample](images/0001-source.png)", encoding="utf-8")
    task = ImageTask(_ref("source.png"), True, "ready", success=True)
    result = RunResult(
        markdown_path=source_md,
        output_markdown_path=output_markdown,
        output_images_dir=output_images_dir,
        tasks=[task],
        success_count=1,
    )

    failures = _process_smoke_failures(result, original_hashes)

    assert "missing run log" in failures
    assert "output image folder is empty" in failures
    assert "backup image folder is empty" in failures
    assert "missing processed image for source.png" in failures
    assert "missing source image backup for source.png" in failures
    assert f"source file changed: {source_image.resolve()}" in failures


def test_task_rows_summarize_image_states(tmp_path: Path) -> None:
    from md_image_inpaint.gui import task_rows
    from md_image_inpaint.models import ImageTask

    ready = ImageTask(_ref("images/ready.png"), True, "ready", mask_path=tmp_path / "ready.png")
    skipped = ImageTask(_ref("https://example.com/remote.png"), False, "remote image skipped")
    failed = ImageTask(_ref("images/failed.png"), True, "ready", error="engine failed")
    processed = ImageTask(_ref("images/done.png"), True, "ready", success=True)

    rows = task_rows([ready, skipped, failed, processed])

    assert rows == [
        ("Ready", "images/ready.png", "ready", str(tmp_path / "ready.png")),
        ("Skipped", "https://example.com/remote.png", "remote image skipped", ""),
        ("Failed", "images/failed.png", "engine failed", ""),
        ("Processed", "images/done.png", "ready", ""),
    ]


def test_result_summary_distinguishes_precheck_from_processing() -> None:
    from md_image_inpaint.gui import result_summary
    from md_image_inpaint.models import ImageTask, RunResult

    ready = ImageTask(_ref("images/ready.png"), True, "ready")
    skipped = ImageTask(_ref("images/skipped.png"), False, "mask missing")
    precheck = RunResult(
        markdown_path=Path("doc.md"),
        output_markdown_path=None,
        output_images_dir=Path("output/images"),
        tasks=[ready, skipped],
        skipped_count=1,
        dry_run=True,
    )
    processed = RunResult(
        markdown_path=Path("doc.md"),
        output_markdown_path=Path("output/document.md"),
        output_images_dir=Path("output/images"),
        success_count=1,
        skipped_count=1,
        failed_count=0,
    )

    assert result_summary(precheck) == "Pre-check complete. Ready 1; skipped 1; issues 0."
    assert result_summary(processed) == "Processed 1; skipped 1; failed 0."


def test_add_skip_patterns_preserves_order_and_avoids_duplicates() -> None:
    from md_image_inpaint.gui import add_skip_patterns

    assert add_skip_patterns(["images/a.png"], ["images/b.png", "images/a.png"]) == [
        "images/a.png",
        "images/b.png",
    ]


def test_gui_exposes_selected_image_skip_controls() -> None:
    gui_source = (Path(__file__).parents[1] / "src" / "md_image_inpaint" / "gui.py").read_text(encoding="utf-8")

    assert "Skip selected" in gui_source
    assert "Clear skips" in gui_source
    assert "\"skip_patterns\": self.skip_patterns" in gui_source
    assert "def _skip_selected(self)" in gui_source


def test_runtime_not_ready_message_distinguishes_precheck_and_processing() -> None:
    from md_image_inpaint.gui import runtime_not_ready_message

    assert "Pre-check can scan" in runtime_not_ready_message(dry_run=True)
    assert "Processing cannot start" in runtime_not_ready_message(dry_run=False)


def test_runtime_check_summary_is_user_readable() -> None:
    from md_image_inpaint.gui import runtime_check_summary

    assert runtime_check_summary(True) == "Runtime is ready."
    assert "See the log" in runtime_check_summary(False)


def test_gui_exposes_standalone_runtime_check() -> None:
    gui_source = (Path(__file__).parents[1] / "src" / "md_image_inpaint" / "gui.py").read_text(encoding="utf-8")

    assert "Check runtime" in gui_source
    assert "self.after(250, self._check_runtime_on_startup)" in gui_source
    assert "def _check_runtime_on_startup(self)" in gui_source
    assert "def _check_runtime(self, startup: bool = False)" in gui_source
    assert "Startup runtime check started." in gui_source
    assert "check_environment(require_iopaint=True)" in gui_source


def test_runtime_progress_status_does_not_show_image_counts() -> None:
    from md_image_inpaint.gui import App
    from md_image_inpaint.models import ProgressEvent

    class Status:
        value = ""

        def set(self, value: str) -> None:
            self.value = value

    class Progress:
        def configure(self, **_kwargs: object) -> None:
            pass

        def __setitem__(self, _key: str, _value: object) -> None:
            pass

    fake_app = object.__new__(App)
    fake_app.status_var = Status()
    fake_app.progress = Progress()

    App._show_progress(
        fake_app,
        ProgressEvent(stage="runtime", message="Runtime is ready.", success_count=4, skipped_count=5, failed_count=6),
    )

    assert fake_app.status_var.value == "Runtime is ready."


def test_message_only_progress_status_does_not_show_empty_counts() -> None:
    from md_image_inpaint.gui import App
    from md_image_inpaint.models import ProgressEvent

    class Status:
        value = ""

        def set(self, value: str) -> None:
            self.value = value

    class Progress:
        def configure(self, **_kwargs: object) -> None:
            pass

        def __setitem__(self, _key: str, _value: object) -> None:
            pass

    fake_app = object.__new__(App)
    fake_app.status_var = Status()
    fake_app.progress = Progress()

    App._show_progress(fake_app, ProgressEvent(stage="processing", message="IOPaint: Downloading model"))

    assert fake_app.status_var.value == "IOPaint: Downloading model"


def test_error_progress_status_does_not_show_image_counts() -> None:
    from md_image_inpaint.gui import App
    from md_image_inpaint.models import ProgressEvent

    class Status:
        value = ""

        def set(self, value: str) -> None:
            self.value = value

    class Progress:
        def configure(self, **_kwargs: object) -> None:
            pass

        def __setitem__(self, _key: str, _value: object) -> None:
            pass

    fake_app = object.__new__(App)
    fake_app.status_var = Status()
    fake_app.progress = Progress()

    App._show_progress(
        fake_app,
        ProgressEvent(stage="error", message="Permission denied.", success_count=4, skipped_count=5, failed_count=6),
    )

    assert fake_app.status_var.value == "Permission denied."


def test_user_facing_error_summarizes_common_failures() -> None:
    from md_image_inpaint.gui import user_facing_error

    assert "Permission denied" in user_facing_error(PermissionError("raw permission detail"))
    assert "could not be found" in user_facing_error(FileNotFoundError("raw file detail"))
    assert "Not enough disk space" in user_facing_error(OSError(errno.ENOSPC, "raw disk detail"))
    assert "See the log" in user_facing_error(RuntimeError("raw runtime detail"))


def test_advanced_settings_are_hidden_by_default() -> None:
    from md_image_inpaint.gui import advanced_settings_default_visible

    assert advanced_settings_default_visible() is False


def _ref(path: str) -> "ImageReference":
    from md_image_inpaint.models import ImageReference

    return ImageReference(
        alt="sample",
        raw_path=path,
        original_text=f"![sample]({path})",
        start=0,
        end=0,
        is_remote=path.startswith("https://"),
        resolved_path=None,
        exists=True,
    )
