import tempfile
import unittest
from pathlib import Path

from zed_pkg_insights.project import discover_zed_roots, find_project_root


class ProjectDiscoveryTests(unittest.TestCase):
    def test_finds_nearest_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            nested = root / "apps" / "web" / "src"
            nested.mkdir(parents=True)
            (root / "apps" / "web" / ".zpkg.toml").write_text(
                '[package]\nname = "web"\n', encoding="utf-8"
            )
            self.assertEqual(find_project_root(nested), root / "apps" / "web")

    def test_uses_native_project_root_before_window_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            app = root / "app"
            source = app / "src"
            source.mkdir(parents=True)
            (app / "Cargo.toml").write_text('[package]\nname="app"\n', encoding="utf-8")
            self.assertEqual(find_project_root(source, [root]), app)


    def test_symlinked_zed_marker_does_not_shadow_native_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "Cargo.toml").write_text('[package]\\nname="app"\\n', encoding="utf-8")
            nested = root / "nested"
            (nested / "src").mkdir(parents=True)
            external = root / "untrusted.toml"
            external.write_text('[package]\\nname="fake"\\n', encoding="utf-8")
            try:
                (nested / ".zpkg.toml").symlink_to(external)
            except (OSError, NotImplementedError) as error:
                self.skipTest("platform does not permit symlinks: {}".format(error))
            self.assertEqual(find_project_root(nested / "src"), root)
            self.assertEqual(discover_zed_roots([nested]), [])

    def test_directory_named_like_lockfile_is_not_a_project_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "Cargo.toml").write_text('[package]\\nname="app"\\n', encoding="utf-8")
            nested = root / "nested"
            (nested / "src").mkdir(parents=True)
            (nested / ".zpkg.lock").mkdir()
            self.assertEqual(find_project_root(nested / "src"), root)
            self.assertEqual(discover_zed_roots([nested]), [])

    def test_regular_manifest_remains_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            nested = root / "app"
            (nested / "src").mkdir(parents=True)
            (nested / ".zpkg.toml").write_text('[package]\\nname="app"\\n', encoding="utf-8")
            self.assertEqual(find_project_root(nested / "src"), nested)
            self.assertEqual(discover_zed_roots([root]), [nested])


if __name__ == "__main__":
    unittest.main()
