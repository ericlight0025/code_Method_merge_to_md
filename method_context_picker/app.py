"""Tkinter 使用介面。"""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .exporter import build_file_context, relative_file_path, write_markdown
from .models import MethodInfo
from .parsers import parse_source, read_source


DARK_PALETTE = {
    "background": "#11151C",
    "surface": "#1A2029",
    "panel": "#202832",
    "editor": "#0D1117",
    "border": "#354152",
    "text": "#E7EDF5",
    "muted": "#99A7B8",
    "accent": "#5ED6E3",
    "accent_active": "#8BEAF0",
    "accent_dark": "#173D45",
}


class MethodContextPickerApp:
    """Method Context Picker 主視窗。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Method Context Picker")
        self.root.geometry("1100x700")
        self.root.minsize(820, 520)

        self.file_methods: dict[Path, list[MethodInfo]] = {}
        self.file_sources: dict[Path, str] = {}
        self.selected_keys: set[str] = set()
        self.method_vars: dict[str, tk.BooleanVar] = {}
        self._file_list_paths: list[Path] = []
        self._method_canvas_window: int | None = None

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="請先加入 Java 或 JavaScript 檔案。")

        self._configure_dark_theme()
        self._build_ui()
        self._refresh_method_list()

    def _configure_dark_theme(self) -> None:
        """設定深色主題，讓檔案選擇與程式碼預覽維持一致的 IDE 風格。"""

        palette = DARK_PALETTE
        self.root.configure(background=palette["background"])
        self.root.option_add("*Font", ("Segoe UI", 10))

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=palette["background"])
        style.configure(
            ".",
            background=palette["surface"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["background"],
        )
        style.configure("TFrame", background=palette["surface"])
        style.configure("Panel.TFrame", background=palette["panel"])
        style.configure("TLabel", background=palette["surface"], foreground=palette["text"])
        style.configure(
            "Panel.TLabel",
            background=palette["panel"],
            foreground=palette["text"],
        )
        style.configure(
            "TLabelframe",
            background=palette["panel"],
            bordercolor=palette["border"],
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=palette["panel"],
            foreground=palette["accent"],
        )
        style.configure(
            "TButton",
            background=palette["surface"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            padding=(10, 6),
        )
        style.map(
            "TButton",
            background=[
                ("pressed", palette["accent_dark"]),
                ("active", palette["accent_dark"]),
            ],
            foreground=[("active", palette["accent_active"])],
        )
        style.configure(
            "TEntry",
            fieldbackground=palette["editor"],
            foreground=palette["text"],
            insertcolor=palette["accent"],
            bordercolor=palette["border"],
            padding=6,
        )
        style.configure(
            "TCheckbutton",
            background=palette["panel"],
            foreground=palette["text"],
            padding=4,
        )
        style.map(
            "TCheckbutton",
            background=[("active", palette["panel"])],
            foreground=[("active", palette["accent_active"])],
        )
        style.configure(
            "Status.TLabel",
            background=palette["editor"],
            foreground=palette["muted"],
            bordercolor=palette["border"],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=palette["surface"],
            troughcolor=palette["editor"],
            bordercolor=palette["border"],
            arrowcolor=palette["muted"],
        )

    def _build_ui(self) -> None:
        """建立主視窗元件。"""

        container = ttk.Frame(self.root, padding=10, style="App.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        title = ttk.Label(
            container,
            text="Method Context Picker",
            font=("Segoe UI", 16, "bold"),
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self._build_file_panel(container)
        self._build_method_panel(container)

        status = ttk.Label(
            container,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padding=(6, 4),
            style="Status.TLabel",
        )
        status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _build_file_panel(self, parent: ttk.Frame) -> None:
        """建立左側檔案清單與檔案操作按鈕。"""

        panel = ttk.LabelFrame(parent, text="檔案", padding=8)
        panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        buttons = ttk.Frame(panel)
        buttons.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(buttons, text="加入檔案", command=self._add_files).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(buttons, text="移除選取", command=self._remove_files).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(buttons, text="清空檔案", command=self._clear_files).pack(side="left")

        list_frame = ttk.Frame(panel)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            width=32,
            background=DARK_PALETTE["editor"],
            foreground=DARK_PALETTE["text"],
            selectbackground=DARK_PALETTE["accent_dark"],
            selectforeground=DARK_PALETTE["accent_active"],
            highlightbackground=DARK_PALETTE["border"],
            highlightcolor=DARK_PALETTE["accent"],
            relief="flat",
            activestyle="none",
        )
        self.file_listbox.grid(row=0, column=0, sticky="nsew")
        file_scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_listbox.yview
        )
        file_scroll.grid(row=0, column=1, sticky="ns")
        self.file_listbox.configure(yscrollcommand=file_scroll.set)

    def _build_method_panel(self, parent: ttk.Frame) -> None:
        """建立右側搜尋、method 清單與輸出按鈕。"""

        panel = ttk.LabelFrame(parent, text="Method / Function", padding=8)
        panel.grid(row=1, column=1, sticky="nsew")
        panel.rowconfigure(2, weight=1)
        panel.columnconfigure(0, weight=1)

        search_frame = ttk.Frame(panel)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="搜尋：").grid(row=0, column=0, padx=(0, 6))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        self.search_var.trace_add("write", lambda *_args: self._refresh_method_list())

        selection_buttons = ttk.Frame(panel)
        selection_buttons.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            selection_buttons,
            text="Select All",
            command=self._select_all_visible,
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            selection_buttons,
            text="Clear",
            command=self._clear_selection,
        ).pack(side="left")

        list_frame = ttk.Frame(panel)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.method_canvas = tk.Canvas(
            list_frame,
            background=DARK_PALETTE["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        self.method_canvas.grid(row=0, column=0, sticky="nsew")
        method_scroll = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.method_canvas.yview,
        )
        method_scroll.grid(row=0, column=1, sticky="ns")
        self.method_canvas.configure(yscrollcommand=method_scroll.set)

        self.method_inner = ttk.Frame(self.method_canvas, style="Panel.TFrame")
        self._method_canvas_window = self.method_canvas.create_window(
            (0, 0), window=self.method_inner, anchor="nw"
        )
        self.method_inner.bind(
            "<Configure>",
            lambda _event: self.method_canvas.configure(
                scrollregion=self.method_canvas.bbox("all")
            ),
        )
        self.method_canvas.bind(
            "<Configure>",
            self._resize_method_inner,
        )

        action_frame = ttk.Frame(panel)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            action_frame,
            text="Preview 原始碼",
            command=self._preview_selected,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            action_frame,
            text="匯出 code.md",
            command=self._export_selected,
        ).pack(side="left")

    def _resize_method_inner(self, event: tk.Event) -> None:
        """讓內層清單寬度跟著 canvas 改變，避免文字被截斷。"""

        if self._method_canvas_window is not None:
            self.method_canvas.itemconfigure(
                self._method_canvas_window,
                width=event.width,
            )

    def _add_files(self) -> None:
        """加入並解析使用者選取的 Java/JavaScript 檔案。"""

        paths = filedialog.askopenfilenames(
            title="選取 Java 或 JavaScript 檔案",
            filetypes=[
                ("Java / JavaScript", "*.java *.js"),
                ("Java", "*.java"),
                ("JavaScript", "*.js"),
                ("所有檔案", "*.*"),
            ],
        )
        if not paths:
            return

        errors: list[str] = []
        added = 0
        for raw_path in paths:
            path = Path(raw_path).expanduser().resolve()
            try:
                source = read_source(path)
                methods = parse_source(source, path)
            except (OSError, ValueError, UnicodeError) as error:
                errors.append(f"{path.name}: {error}")
                continue
            if path not in self.file_methods:
                added += 1
            self.file_methods[path] = methods
            self.file_sources[path] = source

        self._refresh_file_list()
        self._refresh_method_list()
        self._set_status(f"已加入 {added} 個檔案，共找到 {len(self._all_methods())} 個 method/function。")
        if errors:
            messagebox.showwarning("部分檔案無法加入", "\n".join(errors), parent=self.root)

    def _remove_files(self) -> None:
        """移除左側清單目前選取的檔案。"""

        indices = list(self.file_listbox.curselection())
        if not indices:
            messagebox.showinfo("提示", "請先在左側選取要移除的檔案。", parent=self.root)
            return
        for index in indices:
            if 0 <= index < len(self._file_list_paths):
                path = self._file_list_paths[index]
                self.file_methods.pop(path, None)
                self.file_sources.pop(path, None)
                for method in self._methods_for_path(path):
                    self.selected_keys.discard(method.key)
        self._refresh_file_list()
        self._refresh_method_list()
        self._set_status(f"目前載入 {len(self.file_methods)} 個檔案。")

    def _clear_files(self) -> None:
        """清除所有已加入的檔案與勾選狀態。"""

        if not self.file_methods:
            return
        self.file_methods.clear()
        self.file_sources.clear()
        self.selected_keys.clear()
        self._refresh_file_list()
        self._refresh_method_list()
        self._set_status("已清空檔案與勾選狀態。")

    def _refresh_file_list(self) -> None:
        """重新繪製左側檔案清單。"""

        self._file_list_paths = sorted(self.file_methods, key=lambda path: str(path).casefold())
        self.file_listbox.delete(0, tk.END)
        for path in self._file_list_paths:
            count = len(self.file_methods[path])
            self.file_listbox.insert(tk.END, f"{path.name}  ({count} 個)")

    def _refresh_method_list(self) -> None:
        """依搜尋文字重新繪製右側 method checkbox 清單。"""

        for child in self.method_inner.winfo_children():
            child.destroy()
        self.method_vars.clear()

        visible_methods = self._visible_methods()
        if not visible_methods:
            ttk.Label(
                self.method_inner,
                text="目前沒有符合條件的 method/function。",
                padding=8,
            ).pack(anchor="w")
        else:
            for method in visible_methods:
                variable = tk.BooleanVar(value=method.key in self.selected_keys)
                self.method_vars[method.key] = variable
                ttk.Checkbutton(
                    self.method_inner,
                    text=method.display_label,
                    variable=variable,
                    command=lambda key=method.key, var=variable: self._on_toggle(
                        key, var
                    ),
                ).pack(anchor="w", fill="x", padx=4, pady=2)

        self.method_canvas.yview_moveto(0)
        self.method_canvas.configure(scrollregion=self.method_canvas.bbox("all"))

    def _on_toggle(self, key: str, variable: tk.BooleanVar) -> None:
        """同步單一 checkbox 的勾選狀態。"""

        if variable.get():
            self.selected_keys.add(key)
        else:
            self.selected_keys.discard(key)
        self._update_selection_status()

    def _select_all_visible(self) -> None:
        """勾選目前搜尋結果中的所有 method。"""

        for method in self._visible_methods():
            self.selected_keys.add(method.key)
        self._refresh_method_list()
        self._update_selection_status()

    def _clear_selection(self) -> None:
        """清除全部勾選，不受目前搜尋條件限制。"""

        self.selected_keys.clear()
        self._refresh_method_list()
        self._update_selection_status()

    def _preview_selected(self) -> None:
        """在獨立視窗預覽目前勾選的原始碼。"""

        selected = self._selected_methods()
        if not selected:
            messagebox.showinfo("提示", "請先勾選至少一個 method/function。", parent=self.root)
            return

        preview = tk.Toplevel(self.root)
        preview.title("Preview 原始碼")
        preview.geometry("1000x700")
        preview.minsize(600, 400)
        preview.configure(background=DARK_PALETTE["background"])
        text = ScrolledText(
            preview,
            wrap="none",
            font=("Consolas", 10),
            background=DARK_PALETTE["editor"],
            foreground=DARK_PALETTE["text"],
            insertbackground=DARK_PALETTE["accent"],
            selectbackground=DARK_PALETTE["accent_dark"],
            selectforeground=DARK_PALETTE["accent_active"],
            highlightbackground=DARK_PALETTE["border"],
            relief="flat",
        )
        text.pack(fill="both", expand=True, padx=8, pady=8)
        text.insert("1.0", self._build_preview_text(selected))
        text.configure(state="disabled")

    def _export_selected(self) -> None:
        """將目前勾選的 method 匯出成 code.md。"""

        selected = self._selected_methods()
        if not selected:
            messagebox.showinfo("提示", "請先勾選至少一個 method/function。", parent=self.root)
            return

        output = filedialog.asksaveasfilename(
            title="匯出 Markdown",
            defaultextension=".md",
            initialfile="code.md",
            filetypes=[("Markdown", "*.md"), ("所有檔案", "*.*")],
        )
        if not output:
            return
        try:
            path = write_markdown(
                output,
                selected,
                self.file_sources,
                self.file_methods,
            )
        except OSError as error:
            messagebox.showerror("匯出失敗", str(error), parent=self.root)
            return
        self._set_status(f"已匯出 {len(selected)} 個 method：{path}")
        messagebox.showinfo("匯出完成", f"已寫入：\n{path}", parent=self.root)

    def _build_preview_text(self, methods: list[MethodInfo]) -> str:
        """建立保留檔案上下文、只保留已勾選 method 的預覽文字。"""

        chunks: list[str] = []
        selected_keys = {method.key for method in methods}
        paths = sorted({method.file_path for method in methods}, key=lambda item: str(item).casefold())
        for path in paths:
            source = self.file_sources.get(path)
            file_methods = self.file_methods.get(path, methods)
            if source is None:
                continue
            context = build_file_context(source, file_methods, selected_keys)
            chunks.extend(
                [
                    f"===== {path.name}：保留非-method內容與已勾選 method =====",
                    f"FilePath（相對路徑）：{relative_file_path(path, paths)}",
                    context,
                    "",
                ]
            )
        return "\n".join(chunks)

    def _all_methods(self) -> list[MethodInfo]:
        """回傳目前所有檔案的 method，依檔案與行號排序。"""

        methods = [method for values in self.file_methods.values() for method in values]
        return sorted(methods, key=lambda item: (str(item.file_path).casefold(), item.start_offset))

    def _visible_methods(self) -> list[MethodInfo]:
        """依搜尋文字篩選 method。"""

        query = self.search_var.get().strip().casefold()
        methods = self._all_methods()
        if not query:
            return methods
        return [
            method
            for method in methods
            if query in method.name.casefold()
            or query in method.signature.casefold()
            or query in method.file_path.name.casefold()
        ]

    def _selected_methods(self) -> list[MethodInfo]:
        """依勾選 key 取得完整 method 物件。"""

        return [method for method in self._all_methods() if method.key in self.selected_keys]

    def _methods_for_path(self, path: Path) -> list[MethodInfo]:
        """取得指定檔案的 method。"""

        return self.file_methods.get(path, [])

    def _update_selection_status(self) -> None:
        """更新底部的勾選數量提示。"""

        self._set_status(
            f"已勾選 {len(self._selected_methods())} 個，共 {len(self._all_methods())} 個 method/function。"
        )

    def _set_status(self, message: str) -> None:
        """設定狀態列文字。"""

        self.status_var.set(message)


def run() -> None:
    """啟動 Tkinter 應用程式。"""

    root = tk.Tk()
    MethodContextPickerApp(root)
    root.mainloop()
