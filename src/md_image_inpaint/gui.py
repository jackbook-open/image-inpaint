from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from .config import merge_config
from .masks import REGIONS
from .runner import run


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Markdown Image Inpaint")
        self.geometry("780x560")
        self.log_queue: queue.Queue[str] = queue.Queue()

        self.markdown_var = tk.StringVar()
        self.out_var = tk.StringVar(value="output")
        self.mask_var = tk.StringVar()
        self.region_var = tk.StringVar(value="none")
        self.engine_var = tk.StringVar(value="iopaint")
        self.device_var = tk.StringVar(value="cpu")
        self.model_dir_var = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=False)
        self.verbose_var = tk.BooleanVar(value=True)

        self._build()
        self.after(100, self._drain_logs)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(9, weight=1)

        self._path_row(container, 0, "Markdown", self.markdown_var, self._choose_markdown)
        self._path_row(container, 1, "Output", self.out_var, self._choose_output)
        self._path_row(container, 2, "Mask dir", self.mask_var, self._choose_mask_dir)

        ttk.Label(container, text="Region").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(container, textvariable=self.region_var, values=REGIONS, state="readonly").grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(container, text="Engine").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Combobox(container, textvariable=self.engine_var, values=("iopaint",), state="readonly").grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(container, text="Device").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.device_var).grid(row=5, column=1, sticky="ew", pady=4)

        self._path_row(container, 6, "Model dir", self.model_dir_var, self._choose_model_dir)

        checks = ttk.Frame(container)
        checks.grid(row=7, column=1, sticky="w", pady=6)
        ttk.Checkbutton(checks, text="Dry run", variable=self.dry_run_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(checks, text="Verbose", variable=self.verbose_var).pack(side=tk.LEFT)

        actions = ttk.Frame(container)
        actions.grid(row=8, column=1, sticky="e", pady=8)
        ttk.Button(actions, text="Run", command=self._run).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Clear", command=self._clear_log).pack(side=tk.LEFT, padx=4)

        self.log = tk.Text(container, height=18, wrap="word")
        self.log.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=9, column=3, sticky="ns", pady=(8, 0))
        self.log.configure(yscrollcommand=scrollbar.set)

    def _path_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, padx=(8, 0), pady=4)

    def _choose_markdown(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Markdown", "*.md"), ("All files", "*.*")])
        if path:
            self.markdown_var.set(path)

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

    def _run(self) -> None:
        markdown = self.markdown_var.get().strip()
        if not markdown:
            self._append_log("Choose a Markdown file first.")
            return
        self._append_log("Starting...")
        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _run_worker(self) -> None:
        try:
            cli_values = {
                "out_dir": Path(self.out_var.get().strip() or "output"),
                "mask_dir": Path(self.mask_var.get().strip()) if self.mask_var.get().strip() else None,
                "region": self.region_var.get(),
                "engine": self.engine_var.get(),
                "device": self.device_var.get().strip() or "cpu",
                "model_dir": Path(self.model_dir_var.get().strip()) if self.model_dir_var.get().strip() else None,
                "dry_run": self.dry_run_var.get(),
                "verbose": self.verbose_var.get(),
            }
            config = merge_config(Path(self.markdown_var.get().strip()), cli_values)
            result = run(config)
            for line in result.logs:
                self.log_queue.put(line)
            if result.output_markdown_path:
                self.log_queue.put(f"Output Markdown: {result.output_markdown_path}")
        except Exception as exc:  # noqa: BLE001 - GUI should surface all run errors.
            self.log_queue.put(f"Error: {exc}")

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def _clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def _drain_logs(self) -> None:
        while True:
            try:
                self._append_log(self.log_queue.get_nowait())
            except queue.Empty:
                break
        self.after(100, self._drain_logs)


def main() -> None:
    App().mainloop()
