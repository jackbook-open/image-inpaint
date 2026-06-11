from __future__ import annotations

import queue
import threading
import tkinter as tk
from errno import ENOSPC
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import merge_config
from .desktop import (
    check_environment,
    clear_model_cache,
    default_model_dir,
    default_output_dir,
    human_summary,
    open_path,
)
from .masks import REGIONS
from .models import CancelToken, ImageTask, ProgressEvent, RunResult
from .runner import run


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Image Inpaint")
        self.geometry("900x680")
        self.minsize(760, 560)
        self.log_queue: queue.Queue[str | ProgressEvent | RunResult] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_result: RunResult | None = None
        self.cancel_token: CancelToken | None = None
        self.runtime_worker: threading.Thread | None = None
        self.skip_patterns: list[str] = []

        self.markdown_var = tk.StringVar()
        self.out_var = tk.StringVar(value=str(default_output_dir()))
        self.mask_var = tk.StringVar()
        self.region_var = tk.StringVar(value="none")
        self.engine_var = tk.StringVar(value="iopaint")
        self.device_var = tk.StringVar(value="cpu")
        self.model_dir_var = tk.StringVar(value=str(default_model_dir()))
        self.dry_run_var = tk.BooleanVar(value=False)
        self.verbose_var = tk.BooleanVar(value=True)
        self.show_advanced_var = tk.BooleanVar(value=advanced_settings_default_visible())
        self.status_var = tk.StringVar(value="Ready")

        self._build()
        self.after(100, self._drain_logs)
        self.after(250, self._check_runtime_on_startup)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(9, weight=1)

        notice = (
            "Use only documents and images you own or are authorized to modify. "
            "Original files are not changed."
        )
        ttk.Label(container, text=notice, wraplength=820).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self._path_row(container, 1, "Markdown document", self.markdown_var, self._choose_markdown)
        self._path_row(container, 2, "Output folder", self.out_var, self._choose_output)
        self._path_row(container, 3, "Mask folder", self.mask_var, self._choose_mask_dir)

        ttk.Label(container, text="Fallback area").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Combobox(container, textvariable=self.region_var, values=REGIONS, state="readonly").grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(
            container,
            text="Show advanced settings",
            variable=self.show_advanced_var,
            command=self._toggle_advanced,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.advanced_frame = ttk.LabelFrame(container, text="Advanced settings", padding=8)
        self.advanced_frame.columnconfigure(1, weight=1)
        ttk.Label(self.advanced_frame, text="Engine").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(self.advanced_frame, textvariable=self.engine_var, values=("iopaint",), state="readonly").grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ttk.Label(self.advanced_frame, text="Device").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(self.advanced_frame, textvariable=self.device_var).grid(row=1, column=1, sticky="ew", pady=4)
        self._path_row(self.advanced_frame, 2, "Model cache", self.model_dir_var, self._choose_model_dir)

        self.progress = ttk.Progressbar(container, mode="determinate", maximum=100)
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Label(container, textvariable=self.status_var).grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 0))

        actions = ttk.Frame(container)
        actions.grid(row=10, column=0, columnspan=3, sticky="ew", pady=8)
        self.check_button = ttk.Button(actions, text="Pre-check", command=self._precheck)
        self.check_button.pack(side=tk.LEFT, padx=(0, 6))
        self.run_button = ttk.Button(actions, text="Start processing", command=self._run)
        self.run_button.pack(side=tk.LEFT, padx=6)
        self.cancel_button = ttk.Button(actions, text="Cancel", command=self._cancel, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Open output", command=self._open_output).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Open result document", command=self._open_result_document).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="View log", command=self._open_log).pack(side=tk.LEFT, padx=6)
        self.runtime_button = ttk.Button(actions, text="Check runtime", command=self._check_runtime)
        self.runtime_button.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(actions, text="Clear cache", command=self._clear_cache).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(actions, text="Reset defaults", command=self._reset_defaults).pack(side=tk.RIGHT, padx=6)
        ttk.Button(actions, text="Clear log", command=self._clear_log).pack(side=tk.RIGHT, padx=6)

        results = ttk.PanedWindow(container, orient=tk.VERTICAL)
        results.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        image_frame = ttk.LabelFrame(results, text="Images", padding=6)
        log_frame = ttk.LabelFrame(results, text="Log", padding=6)
        results.add(image_frame, weight=1)
        results.add(log_frame, weight=2)

        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        columns = ("status", "image", "reason", "mask")
        self.task_table = ttk.Treeview(image_frame, columns=columns, show="headings", height=7)
        self.task_table.heading("status", text="Status")
        self.task_table.heading("image", text="Image")
        self.task_table.heading("reason", text="Reason")
        self.task_table.heading("mask", text="Mask")
        self.task_table.column("status", width=90, stretch=False)
        self.task_table.column("image", width=260)
        self.task_table.column("reason", width=260)
        self.task_table.column("mask", width=220)
        self.task_table.grid(row=0, column=0, sticky="nsew")
        task_scrollbar = ttk.Scrollbar(image_frame, orient="vertical", command=self.task_table.yview)
        task_scrollbar.grid(row=0, column=1, sticky="ns")
        self.task_table.configure(yscrollcommand=task_scrollbar.set)
        image_actions = ttk.Frame(image_frame)
        image_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(image_actions, text="Skip selected", command=self._skip_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(image_actions, text="Clear skips", command=self._clear_skips).pack(side=tk.LEFT)

        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=12, wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _path_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, padx=(8, 0), pady=4)

    def _choose_markdown(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Markdown", "*.md"), ("All files", "*.*")])
        if path:
            self.markdown_var.set(path)
            self.out_var.set(str(default_output_dir(Path(path))))
            self.skip_patterns = []
            self.task_table.delete(*self.task_table.get_children())

    def _choose_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.out_var.set(path)

    def _choose_mask_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.mask_var.set(path)

    def _choose_model_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.model_dir_var.set(path)

    def _toggle_advanced(self) -> None:
        if self.show_advanced_var.get():
            self.advanced_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        else:
            self.advanced_frame.grid_remove()

    def _run(self) -> None:
        self._start_worker(dry_run=False)

    def _precheck(self) -> None:
        self._start_worker(dry_run=True)

    def _check_runtime_on_startup(self) -> None:
        self._check_runtime(startup=True)

    def _check_runtime(self, startup: bool = False) -> None:
        if self.runtime_worker and self.runtime_worker.is_alive():
            self._append_log("Runtime check is already running.")
            return
        self.runtime_button.configure(state=tk.DISABLED)
        self.status_var.set("Checking runtime...")
        self._append_log("Startup runtime check started." if startup else "Runtime check started.")
        self.runtime_worker = threading.Thread(target=self._check_runtime_worker, daemon=True)
        self.runtime_worker.start()

    def _check_runtime_worker(self) -> None:
        env = check_environment(require_iopaint=True)
        self.log_queue.put(env.user_message)
        for line in env.details:
            self.log_queue.put(line)
        self.log_queue.put(ProgressEvent(stage="runtime", message=runtime_check_summary(env.ok)))

    def _start_worker(self, dry_run: bool) -> None:
        markdown = self.markdown_var.get().strip()
        if not markdown:
            self._append_log("Choose a Markdown document first.")
            return
        if self.worker and self.worker.is_alive():
            self._append_log("A task is already running.")
            return
        self.last_result = None
        self.cancel_token = CancelToken()
        self.status_var.set("Checking runtime...")
        self._set_busy(True)
        self._append_log("Pre-check started." if dry_run else "Processing started.")
        self.worker = threading.Thread(target=self._run_worker, args=(dry_run,), daemon=True)
        self.worker.start()

    def _run_worker(self, dry_run: bool) -> None:
        try:
            env = check_environment(require_iopaint=True)
            self.log_queue.put(env.user_message)
            for line in env.details:
                self.log_queue.put(line)
            if not env.ok:
                message = runtime_not_ready_message(dry_run)
                self.log_queue.put(message)
                self.log_queue.put(ProgressEvent(stage="runtime", message=message))
                if not dry_run:
                    return
            cli_values = {
                "out_dir": Path(self.out_var.get().strip() or "output"),
                "mask_dir": Path(self.mask_var.get().strip()) if self.mask_var.get().strip() else None,
                "region": self.region_var.get(),
                "engine": self.engine_var.get(),
                "device": self.device_var.get().strip() or "cpu",
                "model_dir": Path(self.model_dir_var.get().strip()) if self.model_dir_var.get().strip() else None,
                "dry_run": dry_run,
                "verbose": self.verbose_var.get(),
                "iopaint_cmd": env.iopaint_cmd or "iopaint",
                "skip_patterns": self.skip_patterns,
                "cancel_token": self.cancel_token,
                "progress_callback": self.log_queue.put,
            }
            config = merge_config(Path(self.markdown_var.get().strip()), cli_values)
            result = run(config)
            for line in result.logs:
                self.log_queue.put(line)
            self.log_queue.put(result)
        except Exception as exc:  # noqa: BLE001 - GUI should surface all run errors.
            message = user_facing_error(exc)
            self.log_queue.put(message)
            self.log_queue.put(f"Technical details: {exc}")
            self.log_queue.put(ProgressEvent(stage="error", message=message))

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def _clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def _drain_logs(self) -> None:
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, ProgressEvent):
                self._show_progress(item)
            elif isinstance(item, RunResult):
                self._finish_result(item)
            else:
                self._append_log(item)
        if self.worker and not self.worker.is_alive():
            self._set_busy(False)
        if self.runtime_worker and not self.runtime_worker.is_alive():
            self.runtime_button.configure(state=tk.NORMAL)
        self.after(100, self._drain_logs)

    def _show_progress(self, event: ProgressEvent) -> None:
        if event.total:
            self.progress.configure(mode="determinate", maximum=event.total)
            self.progress["value"] = event.current
        if event.stage in {"runtime", "error"}:
            self.status_var.set(event.message)
            return
        if not event.total and not any((event.success_count, event.skipped_count, event.failed_count)):
            self.status_var.set(event.message)
            return
        self.status_var.set(
            f"{event.message} Success {event.success_count}, skipped {event.skipped_count}, failed {event.failed_count}."
        )

    def _cancel(self) -> None:
        if not self.worker or not self.worker.is_alive() or self.cancel_token is None:
            self._append_log("No running task to cancel.")
            return
        self.cancel_token.cancel()
        self.status_var.set("Cancelling...")
        self._append_log("Cancellation requested. Waiting for the current processing step to stop.")

    def _finish_result(self, result: RunResult) -> None:
        self.last_result = result
        if result.output_markdown_path:
            self._append_log(f"Output document: {result.output_markdown_path}")
        if result.log_path:
            self._append_log(f"Run log: {result.log_path}")
        self._show_tasks(result.tasks)
        summary = result_summary(result)
        self.status_var.set(summary)
        self._append_log(summary)
        title = "Pre-check complete" if result.dry_run else "Processing finished"
        if result.failed_count:
            messagebox.showwarning(f"{title} with issues", summary)
        else:
            messagebox.showinfo(title, summary)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.run_button.configure(state=state)
        self.check_button.configure(state=state)
        self.cancel_button.configure(state=tk.NORMAL if busy else tk.DISABLED)
        if busy:
            self.progress.configure(mode="determinate", maximum=100)
            self.progress["value"] = 0

    def _open_output(self) -> None:
        target = self.last_result.output_markdown_path.parent if self.last_result and self.last_result.output_markdown_path else Path(self.out_var.get())
        self._open_existing(target)

    def _open_result_document(self) -> None:
        if not self.last_result or not self.last_result.output_markdown_path:
            self._append_log("No result document is available yet.")
            return
        self._open_existing(self.last_result.output_markdown_path)

    def _open_log(self) -> None:
        if not self.last_result or not self.last_result.log_path:
            self._append_log("No saved run log is available yet.")
            return
        self._open_existing(self.last_result.log_path)

    def _open_existing(self, path: Path) -> None:
        if not path.exists():
            self._append_log(f"Path does not exist yet: {path}")
            return
        try:
            open_path(path)
        except Exception as exc:  # noqa: BLE001 - desktop open failures should be visible.
            self._append_log(f"Could not open path: {exc}")

    def _clear_cache(self) -> None:
        try:
            target = clear_model_cache(Path(self.model_dir_var.get()) if self.model_dir_var.get().strip() else None)
            self._append_log(f"Model cache cleared: {target}")
        except Exception as exc:  # noqa: BLE001 - GUI should explain maintenance failures.
            self._append_log(f"Could not clear cache: {exc}")

    def _skip_selected(self) -> None:
        selected = self._selected_image_paths()
        if not selected:
            self._append_log("Select one or more images to skip.")
            return
        before = len(self.skip_patterns)
        self.skip_patterns = add_skip_patterns(self.skip_patterns, selected)
        added = len(self.skip_patterns) - before
        for item_id in self.task_table.selection():
            values = list(self.task_table.item(item_id, "values"))
            if len(values) >= 3:
                values[0] = "Skipped"
                values[2] = "selected to skip"
                self.task_table.item(item_id, values=values)
        self._append_log(f"Selected {len(selected)} image(s) to skip; {added} new skip rule(s).")

    def _clear_skips(self) -> None:
        self.skip_patterns = []
        self._append_log("Selected image skips cleared. Run Pre-check again to refresh the image list.")

    def _selected_image_paths(self) -> list[str]:
        paths: list[str] = []
        for item_id in self.task_table.selection():
            values = self.task_table.item(item_id, "values")
            if len(values) >= 2:
                path_text = str(values[1])
                if path_text:
                    paths.append(path_text)
        return paths

    def _show_tasks(self, tasks: list[ImageTask]) -> None:
        self.task_table.delete(*self.task_table.get_children())
        for row in task_rows(tasks):
            self.task_table.insert("", tk.END, values=row)

    def _reset_defaults(self) -> None:
        markdown = Path(self.markdown_var.get()) if self.markdown_var.get().strip() else None
        self.out_var.set(str(default_output_dir(markdown)))
        self.mask_var.set("")
        self.region_var.set("none")
        self.engine_var.set("iopaint")
        self.device_var.set("cpu")
        self.model_dir_var.set(str(default_model_dir()))
        self.verbose_var.set(True)
        self.status_var.set("Defaults restored")
        self._append_log("Defaults restored.")


def task_rows(tasks: list[ImageTask]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for task in tasks:
        if task.success:
            status = "Processed"
        elif task.should_process:
            status = "Failed" if task.error else "Ready"
        else:
            status = "Skipped"
        reason = task.error or task.reason
        mask = str(task.mask_path) if task.mask_path else ""
        rows.append((status, task.reference.raw_path, reason, mask))
    return rows


def add_skip_patterns(existing: list[str], raw_paths: list[str]) -> list[str]:
    merged = list(existing)
    seen = set(merged)
    for raw_path in raw_paths:
        if raw_path not in seen:
            merged.append(raw_path)
            seen.add(raw_path)
    return merged


def result_summary(result: RunResult) -> str:
    if result.dry_run:
        ready_count = sum(1 for task in result.tasks if task.should_process and not task.error)
        return f"Pre-check complete. Ready {ready_count}; skipped {result.skipped_count}; issues {result.failed_count}."
    return human_summary(result.success_count, result.skipped_count, result.failed_count)


def runtime_not_ready_message(dry_run: bool) -> str:
    if dry_run:
        return "Pre-check can scan the document, but processing cannot start until the runtime items above are fixed."
    return "Processing cannot start until the runtime items above are fixed. Run Pre-check again after fixing them."


def runtime_check_summary(ok: bool) -> str:
    if ok:
        return "Runtime is ready."
    return "Runtime needs attention. See the log for missing items and cache location."


def user_facing_error(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "Permission denied. Choose a folder you can write to, or move the document to a normal user folder."
    if isinstance(exc, FileNotFoundError):
        return "A required file could not be found. Run Pre-check to see missing documents, images, or masks."
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == ENOSPC:
        return "Not enough disk space. Free space in the output or model cache location, then try again."
    return "Something went wrong. See the log for details, then try Pre-check again."


def advanced_settings_default_visible() -> bool:
    return False


def main() -> None:
    App().mainloop()
