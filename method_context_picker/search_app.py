"""加入檔名模糊搜尋入口的 Method Context Picker。"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .app import MethodContextPickerApp
from .filename_search import find_files_by_name


class SearchableMethodContextPickerApp(MethodContextPickerApp):
    """在既有 GUI 上增加檔名搜尋，不改動原本解析與匯出流程。"""

    def __init__(self, root: tk.Tk) -> None:
        # 父類別初始化期間會呼叫被覆寫的 _build_ui，因此先建立變數。
        self.filename_root_var = tk.StringVar(master=root)
        self.filename_query_var = tk.StringVar(master=root)
        super().__init__(root)

    def _build_ui(self) -> None:
        """先建立搜尋區，再建立原本的 Method Picker UI。"""

        self._build_filename_search_panel()
        super()._build_ui()

    def _build_filename_search_panel(self) -> None:
        """建立只搜尋檔名的 rg 搜尋區。"""

        panel = ttk.LabelFrame(self.root, text="rg 檔名模糊搜尋", padding=(12, 10))
        panel.pack(fill="x", padx=14, pady=(14, 0))
        panel.columnconfigure(7, weight=1)

        ttk.Label(panel, text="資料夾：").grid(
            row=0, column=0, padx=(0, 7), sticky="w"
        )
        ttk.Entry(panel, textvariable=self.filename_root_var, width=48).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Button(panel, text="選擇", command=self._choose_filename_root).grid(
            row=0, column=2, padx=(7, 0)
        )
        ttk.Separator(panel, orient="vertical").grid(
            row=0, column=3, sticky="ns", padx=16
        )

        ttk.Label(panel, text="檔名：").grid(
            row=0, column=4, padx=(0, 7), sticky="w"
        )
        query_entry = ttk.Entry(panel, textvariable=self.filename_query_var, width=27)
        query_entry.grid(row=0, column=5, sticky="w")
        ttk.Button(panel, text="搜尋", command=self._search_filename).grid(
            row=0, column=6, padx=(7, 0)
        )
        ttk.Label(panel, text="只比對檔名，不搜尋內容", style="Hint.TLabel").grid(
            row=1, column=1, columnspan=6, sticky="w", pady=(6, 0)
        )
        query_entry.bind("<Return>", lambda _event: self._search_filename())

    def _choose_filename_root(self) -> None:
        """選擇要搜尋的專案根目錄。"""

        folder = filedialog.askdirectory(title="選擇程式資料夾")
        if folder:
            self.filename_root_var.set(folder)

    def _search_filename(self) -> None:
        """依檔名搜尋並載入命中的完整檔案。"""

        root_text = self.filename_root_var.get().strip()
        keyword = self.filename_query_var.get().strip()
        if not root_text:
            messagebox.showinfo("提示", "請先選擇資料夾。", parent=self.root)
            return
        if not keyword:
            messagebox.showinfo("提示", "請輸入檔名關鍵字。", parent=self.root)
            return

        try:
            matched_files = find_files_by_name(root_text, keyword)
        except (NotADirectoryError, OSError, RuntimeError) as error:
            messagebox.showerror("搜尋失敗", str(error), parent=self.root)
            return

        # 搜尋結果代表一個新的載入集合，避免殘留上一次的勾選狀態。
        self.file_methods.clear()
        self.file_sources.clear()
        self.selected_keys.clear()
        self._refresh_file_list()
        self._refresh_method_list()

        if not matched_files:
            self._set_status(f"檔名搜尋「{keyword}」：找不到符合檔案。")
            return

        self._load_paths(matched_files)
        self._set_status(f"檔名搜尋「{keyword}」：命中 {len(matched_files)} 支檔案。")


def run() -> None:
    """啟動含檔名搜尋功能的 GUI。"""

    root = tk.Tk()
    SearchableMethodContextPickerApp(root)
    root.mainloop()
