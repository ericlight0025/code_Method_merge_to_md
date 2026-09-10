"""Tkinter 使用介面。"""

from __future__ import annotations

from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .exporter import (
    build_file_context,
    project_file_path,
    write_markdown,
)
from .models import MethodInfo
from .parsers import find_source_files, parse_source, read_source


DARK_PALETTE = {
    "background": "#0F1319",
    "surface": "#151B23",
    "panel": "#1B232D",
    "editor": "#0B0F14",
    "border": "#2C3744",
    "text": "#E3E8EF",
    "muted": "#A3AFBD",
    "accent": "#6CA8A9",
    "accent_active": "#9BC5C3",
    "accent_dark": "#253B3D",
}

PREVIEW_THEME = {
    "heading": "#6CA8A9",
    "filepath": "#A3AFBD",
    "keyword": "#C792EA",
    "type": "#82AAFF",
    "string": "#C3E88D",
    "comment": "#6A9955",
    "number": "#F78C6C",
    "annotation": "#89DDFF",
}

PREVIEW_KEYWORDS = {
    "abstract",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "default",
    "do",
    "else",
    "enum",
    "extends",
    "export",
    "final",
    "finally",
    "for",
    "from",
    "function",
    "get",
    "if",
    "implements",
    "import",
    "in",
    "instanceof",
    "interface",
    "let",
    "new",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "set",
    "static",
    "super",
    "switch",
    "this",
    "throw",
    "throws",
    "try",
    "typeof",
    "var",
    "void",
    "while",
}

PREVIEW_TYPES = {
    "Array",
    "Boolean",
    "Date",
    "Double",
    "Integer",
    "JSON",
    "List",
    "Map",
    "Number",
    "Object",
    "Promise",
    "Set",
    "String",
    "boolean",
    "byte",
    "char",
    "double",
    "float",
    "int",
    "long",
    "number",
    "short",
}

PREVIEW_TOKEN_PATTERN = re.compile(
    r"//.*|/\*.*?\*/|<!--.*?-->|\"(?:\\.|[^\"\\])*\"|"
    r"'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|@\w+|"
    r"\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b"
)


class MethodContextPickerApp:
    """Method Context Picker 主視窗。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Method Context Picker")
        self.root.geometry("1180x700")
        self.root.minsize(960, 620)

        self.file_methods: dict[Path, list[MethodInfo]] = {}
        self.file_sources: dict[Path, str] = {}
        self.selected_keys: set[str] = set()
        self.method_vars: dict[str, tk.BooleanVar] = {}
        self._file_list_paths: list[Path] = []
        self._method_canvas_window: int | None = None

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="請先加入 Java、JavaScript 或 JSP 檔案。")

        self._configure_dark_theme()
        self._build_ui()
        self._refresh_method_list()

    def _configure_dark_theme(self) -> None:
        """設定深色主題，讓檔案選擇與程式碼預覽維持一致的 IDE 風格。"""

        palette = DARK_PALETTE
        self.root.configure(background=palette["background"])
        self.root.option_add("*Font", ("Segoe UI", 11))

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
            "Title.TLabel",
            background=palette["background"],
            foreground=palette["text"],
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=palette["background"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Hint.TLabel",
            background=palette["panel"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "TLabelframe",
            background=palette["panel"],
            bordercolor=palette["border"],
            relief="solid",
            padding=10,
        )
        style.configure(
            "TLabelframe.Label",
            background=palette["panel"],
            foreground=palette["accent"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "TButton",
            background=palette["surface"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            padding=(11, 7),
            font=("Segoe UI", 10),
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
            padding=(8, 7),
            font=("Segoe UI", 11),
        )
        style.configure(
            "TCheckbutton",
            background=palette["panel"],
            foreground=palette["text"],
            padding=(6, 5),
            font=("Segoe UI", 11),
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
            font=("Segoe UI", 10),
        )
        style.configure(
            "Vertical.TSeparator",
            background=palette["border"],
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

        container = ttk.Frame(self.root, padding=14, style="App.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0, minsize=320)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(2, weight=1)

        title = ttk.Label(
            container,
            text="Method Context Picker",
            style="Title.TLabel",
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w")

        subtitle = ttk.Label(
            container,
            text="挑出需要的 method；其他檔案內容會保留在輸出脈絡中",
            style="Subtitle.TLabel",
        )
        subtitle.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))

        self._build_file_panel(container)
        self._build_method_panel(container)

        status = ttk.Label(
            container,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padding=(8, 6),
            style="Status.TLabel",
        )
        status.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_file_panel(self, parent: ttk.Frame) -> None:
        """建立左側檔案清單與檔案操作按鈕。"""

        panel = ttk.LabelFrame(parent, text="檔案", padding=10)
        panel.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        buttons = ttk.Frame(panel)
        buttons.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(buttons, text="加入檔案", command=self._add_files).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(buttons, text="加入資料夾", command=self._add_folder).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(buttons, text="移除", command=self._remove_files).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(buttons, text="清空", command=self._clear_files).pack(side="left")

        list_frame = ttk.Frame(panel)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            width=27,
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

        panel = ttk.LabelFrame(parent, text="Method / Function", padding=10)
        panel.grid(row=2, column=1, sticky="nsew")
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
        """加入使用者選取的 Java/JavaScript 檔案，JSP 則整檔加入。"""

        paths = filedialog.askopenfilenames(
            title="選取 Java、JavaScript 或 JSP 檔案",
            filetypes=[
                ("Java / JavaScript / JSP", "*.java *.js *.jsp"),
                ("Java", "*.java"),
                ("JavaScript", "*.js"),
                ("JSP（完整檔案）", "*.jsp"),
                ("所有檔案", "*.*"),
            ],
        )
        if not paths:
            return

        self._load_paths(paths)

    def _add_folder(self) -> None:
        """遞迴加入資料夾內所有 Java / JavaScript / JSP 檔案。"""

        folder = filedialog.askdirectory(title="選取要遞迴加入的資料夾")
        if not folder:
            return
        try:
            paths = find_source_files(folder)
        except (OSError, ValueError) as error:
            messagebox.showerror("資料夾無法讀取", str(error), parent=self.root)
            return
        if not paths:
            messagebox.showinfo(
                "找不到支援檔案",
                "此資料夾及子資料夾沒有 .java、.js 或 .jsp 檔案。",
                parent=self.root,
            )
            return
        self._load_paths(paths)

    def _load_paths(self, paths: tuple[str, ...] | list[Path]) -> None:
        """讀取、解析並加入一批檔案；JSP 不解析 method，直接保留全文。"""

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
        self._set_status(
            f"已加入 {added} 個檔案，共找到 {len(self._all_methods())} 個 method/function，"
            f"另有 {len(self._whole_file_paths())} 個完整檔案。"
        )
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
                methods = self._methods_for_path(path)
                self.file_methods.pop(path, None)
                self.file_sources.pop(path, None)
                for method in methods:
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
            label = "JSP 完整檔案" if path.suffix.casefold() == ".jsp" else f"{count} 個 method"
            self.file_listbox.insert(tk.END, f"{path.name}  ({label})")

    def _refresh_method_list(self) -> None:
        """依搜尋文字重新繪製右側 method checkbox 清單。"""

        for child in self.method_inner.winfo_children():
            child.destroy()
        self.method_vars.clear()

        visible_methods = self._visible_methods()
        if not visible_methods:
            empty_text = (
                "JSP 以完整檔案加入，不提供 method 勾選。"
                if self.file_methods and not self._all_methods()
                else "目前沒有符合條件的 method/function。"
            )
            ttk.Label(
                self.method_inner,
                text=empty_text,
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
                ).pack(anchor="w", fill="x", padx=5, pady=2)

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
        whole_paths = self._whole_file_paths()
        if not selected and not whole_paths:
            messagebox.showinfo(
                "提示",
                "請先勾選至少一個 method/function，或加入 JSP 完整檔案。",
                parent=self.root,
            )
            return

        preview = tk.Toplevel(self.root)
        preview.title("Preview 原始碼")
        preview.geometry("1000x700")
        preview.minsize(600, 400)
        preview.configure(background=DARK_PALETTE["background"])
        text = ScrolledText(
            preview,
            wrap="none",
            font=("Consolas", 11),
            background=DARK_PALETTE["editor"],
            foreground=DARK_PALETTE["text"],
            insertbackground=DARK_PALETTE["accent"],
            selectbackground=DARK_PALETTE["accent_dark"],
            selectforeground=DARK_PALETTE["accent_active"],
            highlightbackground=DARK_PALETTE["border"],
            relief="flat",
        )
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert("1.0", self._build_preview_text(selected, whole_paths))
        self._apply_preview_theme(text)
        text.configure(state="disabled")

    def _apply_preview_theme(self, text: ScrolledText) -> None:
        """套用內建語法配色，讓 Preview 更接近 IDE 程式碼編輯器。"""

        base_font = ("Consolas", 11)
        text.tag_configure(
            "preview_heading",
            foreground=PREVIEW_THEME["heading"],
            font=("Consolas", 11, "bold"),
        )
        text.tag_configure(
            "preview_filepath",
            foreground=PREVIEW_THEME["filepath"],
            font=("Consolas", 10),
        )
        for tag_name in ("keyword", "type", "string", "comment", "number", "annotation"):
            text.tag_configure(
                f"preview_{tag_name}",
                foreground=PREVIEW_THEME[tag_name],
                font=base_font,
            )
        text.tag_configure(
            "preview_comment",
            foreground=PREVIEW_THEME["comment"],
            font=("Consolas", 11, "italic"),
        )

        for line_number, line in enumerate(text.get("1.0", "end-1c").splitlines(), 1):
            line_start = f"{line_number}.0"
            if line.startswith("====="):
                text.tag_add("preview_heading", line_start, f"{line_number}.end")
                continue
            if line.startswith("FilePath（"):
                text.tag_add("preview_filepath", line_start, f"{line_number}.end")
                continue

            for match in PREVIEW_TOKEN_PATTERN.finditer(line):
                token = match.group(0)
                tag_name = self._preview_token_tag(token)
                if tag_name is None:
                    continue
                start = f"{line_number}.0 + {match.start()} chars"
                end = f"{line_number}.0 + {match.end()} chars"
                text.tag_add(tag_name, start, end)

    @staticmethod
    def _preview_token_tag(token: str) -> str | None:
        """判斷單一程式碼 token 應使用的語法顏色。"""

        if token.startswith(("//", "/*", "<!--")):
            return "preview_comment"
        if token.startswith(("\"", "'", "`")):
            return "preview_string"
        if token.startswith("@"):
            return "preview_annotation"
        if token[0].isdigit():
            return "preview_number"
        if token in PREVIEW_TYPES:
            return "preview_type"
        if token in PREVIEW_KEYWORDS:
            return "preview_keyword"
        return None

    def _export_selected(self) -> None:
        """將勾選的 method 與完整 JSP 檔案匯出成 code.md。"""

        selected = self._selected_methods()
        whole_paths = self._whole_file_paths()
        if not selected and not whole_paths:
            messagebox.showinfo(
                "提示",
                "請先勾選至少一個 method/function，或加入 JSP 完整檔案。",
                parent=self.root,
            )
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
                whole_paths,
            )
        except OSError as error:
            messagebox.showerror("匯出失敗", str(error), parent=self.root)
            return
        self._set_status(
            f"已匯出 {len(selected)} 個 method、{len(whole_paths)} 個完整檔案：{path.name}"
        )
        messagebox.showinfo("匯出完成", f"已寫入檔案：\n{path.name}", parent=self.root)

    def _build_preview_text(
        self,
        methods: list[MethodInfo],
        whole_paths: list[Path],
    ) -> str:
        """建立 method context，並完整保留 JSP 檔案。"""

        chunks: list[str] = []
        selected_keys = {method.key for method in methods}
        paths = sorted(
            {method.file_path for method in methods} | set(whole_paths),
            key=lambda item: str(item).casefold(),
        )
        for path in paths:
            source = self.file_sources.get(path)
            file_methods = self.file_methods.get(path, methods)
            if source is None:
                continue
            is_whole_file = path in whole_paths
            context = source.strip() if is_whole_file else build_file_context(
                source, file_methods, selected_keys
            )
            chunks.extend(
                [
                    f"===== {path.name}："
                    + ("完整 JSP 檔案" if is_whole_file else "保留非-method內容與已勾選 method")
                    + " =====",
                    f"FilePath（專案標籤+路徑）：{project_file_path(path, paths)}",
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

    def _whole_file_paths(self) -> list[Path]:
        """取得不解析 method、匯出時必須完整保留的檔案。"""

        return sorted(
            [path for path in self.file_sources if path.suffix.casefold() == ".jsp"],
            key=lambda path: str(path).casefold(),
        )

    def _update_selection_status(self) -> None:
        """更新底部的勾選數量提示。"""

        self._set_status(
            f"已勾選 {len(self._selected_methods())} 個，共 {len(self._all_methods())} 個 method/function；"
            f"完整檔案 {len(self._whole_file_paths())} 個。"
        )

    def _set_status(self, message: str) -> None:
        """設定狀態列文字。"""

        self.status_var.set(message)


def run() -> None:
    """啟動 Tkinter 應用程式。"""

    root = tk.Tk()
    MethodContextPickerApp(root)
    root.mainloop()
