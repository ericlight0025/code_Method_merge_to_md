"""資料模型。

本檔案只放跨模組共用的資料結構，避免 GUI、解析器與匯出器互相耦合。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MethodInfo:
    """一個可供勾選的 Java method 或 JavaScript function。"""

    file_path: Path
    language: str
    kind: str
    name: str
    signature: str
    start_line: int
    end_line: int
    source: str
    start_offset: int
    end_offset: int

    @property
    def key(self) -> str:
        """回傳在目前專案內穩定且可重建的識別值。"""

        return f"{self.file_path.resolve().as_posix()}::{self.start_offset}"

    @property
    def display_language(self) -> str:
        """回傳給使用者看的語言名稱。"""

        return "Java" if self.language == "java" else "JavaScript"

    @property
    def display_label(self) -> str:
        """回傳清單中使用的簡短標籤。"""

        return (
            f"{self.name}  [{self.kind}]  "
            f"L{self.start_line}-L{self.end_line}  —  {self.file_path.name}"
        )
