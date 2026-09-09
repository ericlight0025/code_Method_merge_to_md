"""Java 與 JavaScript 的輕量內建解析器。

這不是完整語言編譯器，而是針對「快速挑選要放入 AI context 的 method」設計的
穩定啟發式解析器。它會先遮罩註解與字串，再尋找常見的 block method、function
與 arrow function，因此不需要安裝外部 parser 或管理員權限。
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from .models import MethodInfo


SUPPORTED_SUFFIXES = {".java": "java", ".js": "javascript"}

_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"
_CONTROL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "with",
    "synchronized",
}

# 專門處理 function 宣告，讓 function 名稱在清單中比一般 method 更明確。
_FUNCTION_DECLARATION_RE = re.compile(
    rf"""
    ^[ \t]*(?:(?:export)\s+)?(?:(?:default)\s+)?(?:async\s+)?
    function\s*\*?\s*(?P<name>{_IDENTIFIER})\s*
    \([^;{{}}]*\)\s*\{{
    """,
    re.MULTILINE | re.VERBOSE,
)

# Java method、Java constructor、JavaScript class/object method 共用的區塊樣式。
# 先以行首為界，可降低把一般函式呼叫誤判成 method 的機率。
_BLOCK_METHOD_RE = re.compile(
    rf"""
    ^[ \t]*
    (?P<header>[^;{{}}]*
        (?<![A-Za-z0-9_$@])(?P<name>{_IDENTIFIER})\s*
        \([^;{{}}]*\)
        (?:\s+throws\s+[^;{{}}]+)?
        \s*\{{
    )
    """,
    re.MULTILINE | re.VERBOSE,
)

# 支援 const fn = (...) => { ... } 與簡單的 expression-body arrow function。
_ARROW_FUNCTION_RE = re.compile(
    rf"""
    ^[ \t]*(?:export\s+)?(?:const|let|var)\s+
    (?P<name>{_IDENTIFIER})\s*=\s*(?:async\s+)?
    (?:\([^)\n]*\)|{_IDENTIFIER})\s*=>
    """,
    re.MULTILINE | re.VERBOSE,
)


@dataclass(frozen=True)
class _Candidate:
    """解析過程中的中間候選項。"""

    name: str
    kind: str
    start_offset: int
    body_start: int | None
    end_hint: int | None = None


def read_source(path: Path) -> str:
    """以常見編碼讀取原始碼，避免因 BOM 或 Windows 編碼直接中斷。"""

    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp950", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    # 最後仍保留可預覽、可匯出的內容；不可解碼字元以替代符號呈現。
    return raw.decode("utf-8", errors="replace")


def parse_file(file_path: str | Path) -> list[MethodInfo]:
    """解析單一 .java 或 .js 檔案。"""

    path = Path(file_path).expanduser().resolve()
    language = SUPPORTED_SUFFIXES.get(path.suffix.lower())
    if language is None:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(f"不支援的副檔名：{path.suffix or '(無)'}；可用副檔名：{supported}")
    return parse_source(read_source(path), path, language)


def find_source_files(directory: str | Path) -> list[Path]:
    """遞迴尋找資料夾內所有支援的 Java / JavaScript 檔案。"""

    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"不是資料夾：{root}")
    return sorted(
        {
            path.resolve()
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        },
        key=lambda path: str(path).casefold(),
    )


def parse_source(
    source: str,
    file_path: str | Path,
    language: str | None = None,
) -> list[MethodInfo]:
    """解析已載入的原始碼文字。

    ``language`` 可傳入 ``java`` 或 ``javascript``；省略時依檔案副檔名推斷。
    """

    path = Path(file_path).expanduser().resolve()
    resolved_language = language or SUPPORTED_SUFFIXES.get(path.suffix.lower())
    if resolved_language not in {"java", "javascript"}:
        raise ValueError("language 必須是 java 或 javascript")

    masked = _mask_comments_and_strings(source)
    candidates = _collect_candidates(masked, resolved_language)
    return _materialize_candidates(source, path, resolved_language, masked, candidates)


def _collect_candidates(masked: str, language: str) -> list[_Candidate]:
    """從遮罩後文字收集候選 method/function。"""

    candidates: list[_Candidate] = []
    java_class_names = _java_class_names(masked) if language == "java" else set()

    for match in _FUNCTION_DECLARATION_RE.finditer(masked):
        open_index = masked.find("{", match.start(), match.end())
        if open_index >= 0:
            candidates.append(
                _Candidate(
                    name=match.group("name"),
                    kind="function",
                    start_offset=match.start(),
                    body_start=open_index,
                )
            )

    for match in _BLOCK_METHOD_RE.finditer(masked):
        name = match.group("name")
        if name in _CONTROL_KEYWORDS:
            continue
        if name in java_class_names:
            # Java constructor 不是 method，保留在檔案上下文中，不放進勾選清單。
            continue
        name_start = match.start("name")
        if name_start > 0 and masked[name_start - 1] == ".":
            # 排除 if (value.isBlank()) 這類方法呼叫被誤認為宣告。
            continue
        open_index = masked.find("{", match.start(), match.end())
        if open_index >= 0:
            candidates.append(
                _Candidate(
                    name=name,
                    kind="method",
                    start_offset=match.start(),
                    body_start=open_index,
                )
            )

    if language == "javascript":
        for match in _ARROW_FUNCTION_RE.finditer(masked):
            body_start = _first_non_whitespace(masked, match.end())
            if body_start is not None and masked[body_start] == "{":
                candidates.append(
                    _Candidate(
                        name=match.group("name"),
                        kind="function",
                        start_offset=match.start(),
                        body_start=body_start,
                    )
                )
            else:
                end_hint = _find_expression_end(masked, match.end())
                candidates.append(
                    _Candidate(
                        name=match.group("name"),
                        kind="function",
                        start_offset=match.start(),
                        body_start=None,
                        end_hint=end_hint,
                    )
                )

    return candidates


def _java_class_names(masked: str) -> set[str]:
    """取得 Java class 名稱，用來辨識並保留 constructor。"""

    return set(
        re.findall(
            rf"\b(?:class|record|enum)\s+({_IDENTIFIER})",
            masked,
        )
    )


def _materialize_candidates(
    source: str,
    path: Path,
    language: str,
    masked: str,
    candidates: Iterable[_Candidate],
) -> list[MethodInfo]:
    """將候選項轉成完整 source range，並移除同一函式的重複結果。"""

    materialized: list[tuple[_Candidate, int]] = []
    for candidate in candidates:
        if candidate.body_start is not None:
            closing_brace = _find_matching_brace(masked, candidate.body_start)
            if closing_brace is None:
                # 不完整的編輯中檔案先略過，讓 GUI 仍能處理其他檔案。
                continue
            end_offset = closing_brace + 1
        else:
            end_offset = candidate.end_hint or len(source)

        if end_offset <= candidate.start_offset:
            continue
        materialized.append((candidate, end_offset))

    # function 宣告與一般 block pattern 可能命中同一個 opening brace，保留較
    # 明確的 function 標籤，避免清單出現兩筆相同項目。以 opening brace 去重，
    # 也能避免一般 pattern 從前一行註解的空白位置開始匹配而產生重複。
    unique: dict[tuple[str, int], tuple[_Candidate, int]] = {}
    for candidate, end_offset in materialized:
        if candidate.body_start is not None:
            identity = ("block", candidate.body_start)
        else:
            identity = ("expression", candidate.start_offset)
        existing = unique.get(identity)
        if existing is None or (
            candidate.kind == "function" and existing[0].kind != "function"
        ):
            unique[identity] = (candidate, end_offset)

    line_starts = _line_starts(source)
    results: list[MethodInfo] = []
    for candidate, end_offset in sorted(
        unique.values(), key=lambda item: item[0].start_offset
    ):
        start_offset = candidate.start_offset
        raw_source = source[start_offset:end_offset]
        if not raw_source.strip():
            continue
        body_start = candidate.body_start
        signature_end = (body_start + 1) if body_start is not None else end_offset
        signature = _compact_signature(source[start_offset:signature_end])
        results.append(
            MethodInfo(
                file_path=path,
                language=language,
                kind=candidate.kind,
                name=candidate.name,
                signature=signature,
                start_line=_line_number(line_starts, start_offset),
                end_line=_line_number(line_starts, max(start_offset, end_offset - 1)),
                source=raw_source,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
    return results


def _mask_comments_and_strings(source: str) -> str:
    """以等長空白遮罩註解與字串，保留換行與程式碼位置。"""

    chars = list(source)
    length = len(source)
    index = 0
    state: str | None = None

    def blank(position: int) -> None:
        if chars[position] not in "\r\n":
            chars[position] = " "

    while index < length:
        current = source[index]
        next_char = source[index + 1] if index + 1 < length else ""

        if state is None:
            if current == "/" and next_char == "/":
                blank(index)
                blank(index + 1)
                index += 2
                state = "line_comment"
                continue
            if current == "/" and next_char == "*":
                blank(index)
                blank(index + 1)
                index += 2
                state = "block_comment"
                continue
            if source.startswith('"""', index):
                for offset in range(3):
                    blank(index + offset)
                index += 3
                state = "text_block"
                continue
            if current in {"'", '"', "`"}:
                blank(index)
                state = current
                index += 1
                continue
            index += 1
            continue

        if state == "line_comment":
            if current in "\r\n":
                state = None
            else:
                blank(index)
            index += 1
            continue

        if state == "block_comment":
            if current == "*" and next_char == "/":
                blank(index)
                blank(index + 1)
                index += 2
                state = None
            else:
                blank(index)
                index += 1
            continue

        if state == "text_block":
            if source.startswith('"""', index):
                for offset in range(3):
                    blank(index + offset)
                index += 3
                state = None
            else:
                blank(index)
                index += 1
            continue

        # 其餘 state 都是單引號、雙引號或 JavaScript template literal。
        if current == "\\":
            blank(index)
            if index + 1 < length:
                blank(index + 1)
            index += 2
        else:
            blank(index)
            if current == state:
                state = None
            index += 1

    return "".join(chars)


def _find_matching_brace(masked: str, opening_index: int) -> int | None:
    """找出與 opening brace 對應的 closing brace。"""

    if opening_index < 0 or opening_index >= len(masked) or masked[opening_index] != "{":
        return None
    depth = 0
    for index in range(opening_index, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _first_non_whitespace(text: str, start: int) -> int | None:
    """找出 start 之後第一個非空白字元位置。"""

    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return index if index < len(text) else None


def _find_expression_end(masked: str, start: int) -> int:
    """找出簡單 arrow expression 的結尾。"""

    semicolon = masked.find(";", start)
    newline = masked.find("\n", start)
    if semicolon >= 0 and (newline < 0 or semicolon < newline):
        return semicolon + 1
    if newline >= 0:
        return newline
    return len(masked)


def _compact_signature(text: str) -> str:
    """將 method header 壓成適合清單與 markdown metadata 的單行文字。"""

    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= 180 else compact[:177] + "..."


def _line_starts(source: str) -> list[int]:
    """建立每一行的起始 offset。"""

    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
    return starts


def _line_number(starts: list[int], offset: int) -> int:
    """由 offset 計算 1-based 行號。"""

    return bisect_right(starts, offset)
