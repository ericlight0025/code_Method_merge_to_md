"""以 Python 標準函式庫執行本專案測試。"""

from __future__ import annotations

import sys
import unittest


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
