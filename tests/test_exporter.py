"""Markdown 匯出器自動化測試。"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from method_context_picker.exporter import build_file_context, build_markdown, write_markdown
from method_context_picker.parsers import parse_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ExporterTests(unittest.TestCase):
    """驗證輸出內容、排序與檔案編碼。"""

    def test_build_markdown_contains_metadata_and_source(self) -> None:
        methods = parse_file(PROJECT_ROOT / "fixtures" / "Example.java")
        selected = [methods[1], methods[0]]
        markdown = build_markdown(selected)

        self.assertIn("# Method Context", markdown)
        self.assertIn("已選取 2 個 method/function。", markdown)
        self.assertIn("`greet`", markdown)
        self.assertIn("`add`", markdown)
        self.assertIn("public String greet", markdown)
        self.assertIn("```java", markdown)
        self.assertLess(markdown.index("`greet`"), markdown.index("`add`"))

    def test_empty_selection_is_explicit(self) -> None:
        self.assertEqual(
            build_markdown([]),
            "# Method Context\n\n目前沒有勾選任何 method。\n",
        )

    def test_write_markdown_uses_utf8(self) -> None:
        methods = parse_file(PROJECT_ROOT / "fixtures" / "example.js")[:1]
        with tempfile.TemporaryDirectory() as temporary:
            output = write_markdown(Path(temporary) / "code.md", methods)
            self.assertTrue(output.exists())
            content = output.read_text(encoding="utf-8")
            self.assertIn("JavaScript function", content)
            self.assertIn("fetchUser", content)

    def test_selected_method_keeps_non_method_file_context(self) -> None:
        source_path = PROJECT_ROOT / "fixtures" / "spring_boot_demo" / "src" / "main" / "java" / "demo" / "GreetingController.java"
        source = source_path.read_text(encoding="utf-8")
        methods = parse_file(source_path)
        selected = [next(method for method in methods if method.name == "hello")]

        context = build_file_context(source, methods, {selected[0].key})
        self.assertIn("package demo;", context)
        self.assertIn("import java.util.Map;", context)
        self.assertIn("@RestController", context)
        self.assertIn("private final GreetingService greetingService;", context)
        self.assertIn("public GreetingController(GreetingService", context)
        self.assertIn("public Map<String, String> hello", context)

        markdown = build_markdown(
            selected,
            {source_path.resolve(): source},
            {source_path.resolve(): methods},
        )
        self.assertIn("## Source Context", markdown)
        self.assertIn("private final GreetingService greetingService;", markdown)
        self.assertIn(
            "FilePath（相對路徑）：`src/main/java/demo/GreetingController.java`",
            markdown,
        )


if __name__ == "__main__":
    unittest.main()
