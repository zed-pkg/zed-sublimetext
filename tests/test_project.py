import tempfile
import unittest
from pathlib import Path

from zed_pkg_insights.project import find_project_root


class ProjectDiscoveryTests(unittest.TestCase):
    def test_finds_nearest_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "apps" / "web" / "src"
            nested.mkdir(parents=True)
            (root / "apps" / "web" / ".zpkg.toml").write_text(
                '[package]\nname = "web"\n', encoding="utf-8"
            )
            self.assertEqual(find_project_root(nested), root / "apps" / "web")

    def test_uses_native_project_root_before_window_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app"
            source = app / "src"
            source.mkdir(parents=True)
            (app / "Cargo.toml").write_text('[package]\nname="app"\n', encoding="utf-8")
            self.assertEqual(find_project_root(source, [root]), app)


if __name__ == "__main__":
    unittest.main()
