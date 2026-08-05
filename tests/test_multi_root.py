import tempfile
import unittest
from pathlib import Path

from zed_pkg_insights.project import discover_zed_roots

class MultiRootTests(unittest.TestCase):
    def test_discovers_root_and_nested_packages_across_window_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "first"
            nested = first / "packages" / "nested"
            second = base / "second"
            nested.mkdir(parents=True)
            second.mkdir()
            (first / ".zpkg.toml").write_text("[package]\n")
            (nested / ".zpkg.toml").write_text("[package]\n")
            (second / ".zpkg.lock").write_text("version = 1\n")
            roots = discover_zed_roots([first, second])
            self.assertEqual({first.resolve(), nested.resolve(), second.resolve()}, set(roots))

if __name__ == "__main__":
    unittest.main()
