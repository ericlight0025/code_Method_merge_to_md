"""檔名模糊搜尋自動化測試。"""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from method_context_picker.filename_search import find_files_by_name


class FilenameSearchTests(unittest.TestCase):
    """驗證只比對檔名、支援副檔名與 fallback 行為。"""

    @patch("method_context_picker.filename_search.shutil.which", return_value="rg")
    @patch("method_context_picker.filename_search.subprocess.run")
    def test_case_insensitive_filename_search(self, mock_run, _mock_which) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["rg", "--files"],
            returncode=0,
            stdout=(
                "src/PolicyController.java\n"
                "src/ContractService.java\n"
                "web/policycontroller.js\n"
                "web/policy.jsp\n"
            ),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temporary:
            result = find_files_by_name(temporary, "CONTROLLER")

        self.assertEqual(
            [path.name for path in result],
            ["PolicyController.java", "policycontroller.js"],
        )
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.args[0][1:3], ["--files", "--color"])

    @patch("method_context_picker.filename_search.shutil.which", return_value="rg")
    @patch("method_context_picker.filename_search.subprocess.run")
    def test_directory_name_does_not_match(self, mock_run, _mock_which) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["rg", "--files"],
            returncode=0,
            stdout="controller/ABCService.java\nservice/TestController.java\n",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temporary:
            result = find_files_by_name(temporary, "controller")

        self.assertEqual([path.name for path in result], ["TestController.java"])

    def test_fallback_without_rg(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "PolicyController.java").write_text("class Demo {}", encoding="utf-8")
            (root / "policy.jsp").write_text("<h1>Demo</h1>", encoding="utf-8")
            (root / "controller" / "nested").mkdir(parents=True)
            (root / "controller" / "nested" / "OtherService.java").write_text(
                "class Other {}", encoding="utf-8"
            )

            with patch("method_context_picker.filename_search.shutil.which", return_value=None):
                result = find_files_by_name(root, "controller")

        self.assertEqual([path.name for path in result], ["PolicyController.java"])

    def test_empty_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(find_files_by_name(temporary, "   "), [])


if __name__ == "__main__":
    unittest.main()
