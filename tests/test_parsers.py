"""解析器自動化測試。"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from method_context_picker.parsers import find_source_files, parse_file, parse_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "fixtures"


class ParserTests(unittest.TestCase):
    """驗證 Java 與 JavaScript 常見寫法，以及字串/註解遮罩。"""

    def test_parse_java_fixture(self) -> None:
        methods = parse_file(FIXTURES / "Example.java")
        names = [method.name for method in methods]

        self.assertEqual(
            names,
            ["greet", "add", "calculateTotal", "log"],
        )
        self.assertTrue(all(method.language == "java" for method in methods))
        greet = next(method for method in methods if method.name == "greet")
        self.assertIn("return prefix + name +", greet.source)
        self.assertLess(greet.start_line, greet.end_line)

    def test_parse_javascript_fixture(self) -> None:
        methods = parse_file(FIXTURES / "example.js")
        names = [method.name for method in methods]

        self.assertEqual(
            names,
            [
                "fetchUser",
                "formatName",
                "doubleValue",
                "constructor",
                "total",
                "addItem",
                "save",
                "fake",
            ],
        )
        self.assertEqual(methods[0].kind, "function")
        self.assertEqual(
            next(method for method in methods if method.name == "doubleValue").source,
            "const doubleValue = (value) => value * 2;",
        )

    def test_comments_and_strings_are_not_parsed(self) -> None:
        source = """
        // function hidden() { return 1; }
        const text = "{ function alsoHidden() { return 2; } }";
        /* public void hiddenJava() { } */
        public void visible() {
            String body = "}";
        }
        """
        methods = parse_source(source, "Masking.java")

        self.assertEqual([method.name for method in methods], ["visible"])
        self.assertIn('String body = "}";', methods[0].source)

    def test_unfinished_method_is_skipped_without_crashing(self) -> None:
        source = "function complete() { return true; }\nfunction unfinished() {\n"
        methods = parse_source(source, "unfinished.js")

        self.assertEqual([method.name for method in methods], ["complete"])

    def test_utf8_bom_and_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            java_path = Path(temporary) / "Bom.java"
            java_path.write_bytes(
                "\ufeffpublic class Bom {\n    public void run() { }\n}\n".encode("utf-8")
            )
            self.assertEqual([method.name for method in parse_file(java_path)], ["run"])

            text_path = Path(temporary) / "notes.txt"
            text_path.write_text("void no();", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_file(text_path)

    def test_parse_spring_boot_fixture(self) -> None:
        spring_root = FIXTURES / "spring_boot_demo" / "src" / "main" / "java" / "demo"

        application_methods = parse_file(spring_root / "SpringBootDemoApplication.java")
        controller_methods = parse_file(spring_root / "GreetingController.java")
        service_methods = parse_file(spring_root / "GreetingService.java")

        self.assertEqual([method.name for method in application_methods], ["main"])
        self.assertEqual(
            [method.name for method in controller_methods],
            ["hello"],
        )
        self.assertEqual(
            [method.name for method in service_methods],
            ["greet", "normalizeName"],
        )
        hello = next(method for method in controller_methods if method.name == "hello")
        self.assertIn("@GetMapping(\"/hello\")", hello.source)

    def test_find_source_files_recursively(self) -> None:
        files = find_source_files(FIXTURES)
        self.assertEqual(
            [path.relative_to(FIXTURES).as_posix() for path in files],
            [
                "Example.java",
                "example.js",
                "spring_boot_demo/src/main/java/demo/GreetingController.java",
                "spring_boot_demo/src/main/java/demo/GreetingService.java",
                "spring_boot_demo/src/main/java/demo/SpringBootDemoApplication.java",
            ],
        )


if __name__ == "__main__":
    unittest.main()
