"""使用 ripgrep 依檔名進行快速模糊搜尋。

優先使用 ``rg --files`` 取得檔案清單，只比對檔名，不讀取檔案內容；
如果電腦沒有安裝 ripgrep，則退回 Python 內建遞迴搜尋，維持 GUI 可用。
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .parsers import SUPPORTED_SUFFIXES


def find_files_by_name(
    directory: str | Path,
    keyword: str,
    rg_executable: str = "rg",
) -> list[Path]:
    """依檔名包含關鍵字搜尋 Java、JavaScript 與 JSP 檔案。"""

    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"不是有效資料夾：{root}")

    query = keyword.strip().casefold()
    if not query:
        return []

    if shutil.which(rg_executable) is not None:
        return _find_with_rg(root, query, rg_executable)

    # rg 是加速工具，不應該讓整個 Method Picker 因未安裝 rg 而無法使用。
    return _find_with_python(root, query)


def _find_with_rg(root: Path, query: str, rg_executable: str) -> list[Path]:
    """使用 rg 取得相對檔案清單，再只比對檔名。"""

    result = subprocess.run(
        [rg_executable, "--files", "--color", "never"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode not in {0, 1}:
        error_message = result.stderr.strip() or f"return code = {result.returncode}"
        raise RuntimeError(f"rg 執行失敗：{error_message}")

    matched: set[Path] = set()
    for line in result.stdout.splitlines():
        relative_path = Path(line.strip())
        if not relative_path.name:
            continue
        if relative_path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            continue
        if query in relative_path.name.casefold():
            matched.add((root / relative_path).resolve())

    return sorted(matched, key=lambda path: str(path).casefold())


def _find_with_python(root: Path, query: str) -> list[Path]:
    """沒有 rg 時，以 Python 內建遞迴搜尋提供 graceful fallback。"""

    matched: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.casefold() in SUPPORTED_SUFFIXES and query in path.name.casefold():
            matched.append(path.resolve())
    return sorted(set(matched), key=lambda path: str(path).casefold())
