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
            "FilePath（專案標籤+路徑）：`spring_boot_demo/src/main/java/demo/GreetingController.java`",
            markdown,
        )
        self.assertNotIn("C:/Users/", markdown)
        self.assertNotIn("javalight", markdown)

    def test_jsp_exports_as_a_complete_file(self) -> None:
        """沒有 method 勾選時，JSP 仍應以完整檔案匯出。"""

        jsp_path = PROJECT_ROOT / "fixtures" / "example.jsp"
        source = jsp_path.read_text(encoding="utf-8")
        resolved_path = jsp_path.resolve()

        markdown = build_markdown(
            [],
            {resolved_path: source},
            {resolved_path: []},
            [resolved_path],
        )

        self.assertIn("已選取 0 個 method/function，另含 1 個完整檔案。", markdown)
        self.assertIn("完整保留 JSP 檔案。", markdown)
        self.assertIn("${title}", markdown)
        self.assertIn(
            "FilePath（專案標籤+路徑）：`fixtures/example.jsp`",
            markdown,
        )
        self.assertNotIn("C:/Users/", markdown)
        self.assertNotIn("javalight", markdown)

    def test_project_file_path_handles_cross_drive_gracefully(self) -> None:
        """跨磁碟機或無共同路徑時，不應拋出 ValueError。"""
        from method_context_picker.exporter import project_file_path

        path_c = Path("C:/projectA/file1.java")
        path_d = Path("D:/projectB/file2.java")
        result = project_file_path(path_c, [path_c, path_d])
        self.assertTrue(result.endswith("file1.java"))


if __name__ == "__main__":
    unittest.main()
