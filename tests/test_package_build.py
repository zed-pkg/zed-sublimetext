import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-package.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_package", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageBuildTests(unittest.TestCase):
    def test_build_is_deterministic_and_excludes_development_files(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.sublime-package"
            second = Path(directory) / "second.sublime-package"
            builder.build_package(ROOT, first)
            builder.build_package(ROOT, second)

            self.assertEqual(first.read_bytes(), second.read_bytes())

            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                self.assertEqual(len(names), len(set(names)))
                self.assertIn("zed_sublimetext.py", names)
                self.assertIn("zed_pkg_insights/analyzer.py", names)
                self.assertIn("Default.sublime-commands", names)
                self.assertIn("Main.sublime-menu", names)
                self.assertIn("ZedPackageInsights.sublime-settings", names)
                self.assertIn("messages.json", names)
                self.assertIn("LICENSE", names)

                if (ROOT / "zed_pkg_insights" / "_vendor" / "tomli" / "_parser.py").exists():
                    self.assertIn("zed_pkg_insights/_vendor/tomli/_parser.py", names)
                    self.assertIn("zed_pkg_insights/_vendor/tomli/LICENSE", names)

                forbidden_prefixes = (".git/", ".github/", "dist/", "scripts/", "tests/")
                self.assertFalse(any(name.startswith(forbidden_prefixes) for name in names))
                self.assertNotIn(".zpkg.toml", names)
                self.assertNotIn(".zpkg.lock", names)
                self.assertNotIn("pyproject.toml", names)
                self.assertTrue(all(info.date_time == builder.FIXED_TIMESTAMP for info in archive.infolist()))


if __name__ == "__main__":
    unittest.main()
