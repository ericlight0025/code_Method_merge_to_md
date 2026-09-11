"""將勾選的 method 匯出為 code.md。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import re
from typing import Iterable

from .models import MethodInfo


def build_markdown(
    methods: Iterable[MethodInfo],
    file_sources: Mapping[Path, str] | None = None,
    all_methods_by_file: Mapping[Path, Sequence[MethodInfo]] | None = None,
    whole_file_paths: Iterable[Path] | None = None,
) -> str:
    """建立可直接貼到 ChatGPT、Copilot 或 issue 的 Markdown context。

    提供檔案原始碼時，會保留選取檔案中的非-method內容，只移除未勾選的
    method。這能保留 package、import、annotation、class 宣告與欄位變數。
    """

    selected = sorted(
        methods,
        key=lambda method: (str(method.file_path).casefold(), method.start_offset),
    )
    whole_paths = sorted(
        {Path(path).resolve() for path in (whole_file_paths or ())},
        key=lambda path: str(path).casefold(),
    )
    if not selected and not whole_paths:
        return "# Method Context\n\n目前沒有勾選任何 method。\n"

    selected_paths = sorted(
        {method.file_path for method in selected},
        key=lambda item: str(item).casefold(),
    )

    lines = [
        "# Method Context",
        "",
        _selection_summary(len(selected), len(whole_paths)),
        "",
    ]

    if file_sources is not None:
        return _build_file_context_markdown(
            lines,
            selected,
            file_sources,
            all_methods_by_file or {},
            whole_paths,
        )

    for index, method in enumerate(selected, start=1):
        fence = _code_fence(method.source)
        language = "java" if method.language == "java" else "javascript"
        project_path = project_file_path(method.file_path, selected_paths)
        lines.extend(
            [
                f"## {index}. `{method.name}`",
                f"- FilePath（專案標籤+路徑）：`{project_path}`",
                f"- 類型：{method.display_language} {method.kind}",
                f"- 行號：L{method.start_line}-L{method.end_line}",
                f"- Signature：`{_escape_inline_code(method.signature)}`",
                "",
                f"{fence}{language}",
                method.source.rstrip("\r\n"),
                fence,
                "",
            ]
        )
    return "\n".join(lines)


def write_markdown(
    output_path: str | Path,
    methods: Iterable[MethodInfo],
    file_sources: Mapping[Path, str] | None = None,
    all_methods_by_file: Mapping[Path, Sequence[MethodInfo]] | None = None,
    whole_file_paths: Iterable[Path] | None = None,
) -> Path:
    """將 Markdown 以 UTF-8 寫入指定位置，回傳供程式內部使用的路徑。"""

    path = Path(output_path).expanduser().resolve()
    path.write_text(
        build_markdown(
            methods,
            file_sources,
            all_methods_by_file,
            whole_file_paths,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def build_file_context(
    source: str,
    all_methods: Sequence[MethodInfo],
    selected_keys: set[str],
) -> str:
    """保留非-method內容與勾選的 method，移除未勾選的 method。"""

    mask = bytearray(b"\x01" * len(source))

    # 1. 標記所有 method 範圍為要移除 (0)
    for method in all_methods:
        mask[method.start_offset:method.end_offset] = b"\x00" * (
            method.end_offset - method.start_offset
        )

    # 2. 標記已勾選的 method 範圍為保留 (1)
    # 這會一併蓋過巢狀 function 中，被外層標記為 0 的部分，確保選取內層時不會被外層隱藏。
    for method in all_methods:
        if method.key in selected_keys:
            mask[method.start_offset:method.end_offset] = b"\x01" * (
                method.end_offset - method.start_offset
            )

    from itertools import compress
    return "".join(compress(source, mask)).strip()


def _build_file_context_markdown(
    lines: list[str],
    selected: list[MethodInfo],
    file_sources: Mapping[Path, str],
    all_methods_by_file: Mapping[Path, Sequence[MethodInfo]],
    whole_file_paths: Sequence[Path],
) -> str:
    """建立以檔案為單位的 context，讓非-method程式碼保持完整。"""

    selected_keys = {method.key for method in selected}
    selected_by_file: dict[Path, list[MethodInfo]] = {}
    for method in selected:
        selected_by_file.setdefault(method.file_path, []).append(method)

    lines.extend(["## Selected methods", ""])
    selected_paths = sorted(
        set(selected_by_file) | set(whole_file_paths),
        key=lambda item: str(item).casefold(),
    )
    for method in selected:
        lines.append(
            f"- `{method.name}` — `{method.file_path.name}` "
            f"(L{method.start_line}-L{method.end_line})；"
            f"FilePath（專案標籤+路徑）：`{project_file_path(method.file_path, selected_paths)}`"
        )
    lines.extend(["", "## Source Context", ""])

    for path in selected_paths:
        source = file_sources.get(path)
        if source is None:
            continue
        methods = all_methods_by_file.get(path, selected_by_file.get(path, []))
        context = (
            source.strip()
            if path in whole_file_paths
            else build_file_context(source, methods, selected_keys)
        )
        language = _markdown_language(path, selected_by_file.get(path, []))
        fence = _code_fence(context)
        lines.extend(
            [
                f"### `{path.name}`",
                f"FilePath（專案標籤+路徑）：`{project_file_path(path, selected_paths)}`；"
                + ("完整保留 JSP 檔案。" if path in whole_file_paths else "保留非-method內容與已勾選 method。"),
                "",
                f"{fence}{language}",
                context,
                fence,
                "",
            ]
        )
    return "\n".join(lines)


def _selection_summary(method_count: int, whole_file_count: int) -> str:
    """建立同時包含 method 與完整檔案的選取摘要。"""

    if whole_file_count:
        return (
            f"已選取 {method_count} 個 method/function，"
            f"另含 {whole_file_count} 個完整檔案。"
        )
    return f"已選取 {method_count} 個 method/function。"


def project_file_path(path: Path, all_paths: Sequence[Path]) -> str:
    """回傳專案標籤加上專案內路徑，方便跨機器辨識檔案。"""

    resolved_path = Path(path).resolve()
    project_roots = {
        ancestor.parent
        for item in all_paths
        for ancestor in [Path(item).resolve().parent, *Path(item).resolve().parents]
        if ancestor.name.casefold() == "src"
    }
    if len(project_roots) == 1:
        project_root = next(iter(project_roots))
    else:
        parents = [str(Path(item).resolve().parent) for item in all_paths]
        try:
            project_root = Path(os.path.commonpath(parents)) if parents else resolved_path.parent
        except ValueError:
            project_root = resolved_path.parent
    try:
        relative = Path(os.path.relpath(resolved_path, project_root)).as_posix()
    except ValueError:
        relative = resolved_path.name
    return f"{project_root.name}/{relative}"


def _markdown_language(path: Path, methods: Sequence[MethodInfo]) -> str:
    """依 method 或副檔名選擇 Markdown code fence 語言。"""

    if methods:
        return "java" if methods[0].language == "java" else "javascript"
    return {".java": "java", ".js": "javascript", ".jsp": "jsp"}.get(
        path.suffix.casefold(), "text"
    )


def relative_file_path(path: Path, all_paths: Sequence[Path]) -> str:
    """以專案 source root 或共同父資料夾建立可攜式相對路徑。"""

    resolved_path = Path(path).resolve()
    resolved_parents = [str(Path(item).resolve().parent) for item in all_paths]
    if not resolved_parents:
        return resolved_path.name
    try:
        source_roots = {
            ancestor.parent
            for item in all_paths
            for ancestor in [Path(item).resolve().parent, *Path(item).resolve().parents]
            if ancestor.name.casefold() == "src"
        }
        if len(source_roots) == 1:
            base_path = next(iter(source_roots))
        else:
            base_path = Path(os.path.commonpath(resolved_parents))
        return Path(os.path.relpath(resolved_path, base_path)).as_posix()
    except ValueError:
        # 不同磁碟機無法計算共同路徑時，至少提供不含使用者目錄的檔名。
        return resolved_path.name


def _code_fence(source: str) -> str:
    """選擇不會被原始碼內 backtick 提前關閉的 fenced code marker。"""

    runs = re.findall(r"`+", source)
    longest = max((len(run) for run in runs), default=2)
    return "`" * max(3, longest + 1)


def _escape_inline_code(text: str) -> str:
    """避免 signature 內的 backtick 破壞 inline code。"""

    return text.replace("`", "\\`")
