import os
import tempfile
import time
import unittest
from pathlib import Path

from zed_pkg_insights.analyzer import Analyzer
from zed_pkg_insights.runner import CommandResult


class FakeRunner:
    def __init__(self, version="zed 0.1.0", help_text="universal package manager"):
        self.version = version
        self.help_text = help_text

    def run(self, argv, cwd, timeout_seconds=15.0, extra_env=None):
        if "--version" in argv:
            return CommandResult(tuple(argv), 0, self.version + "\n", "")
        return CommandResult(tuple(argv), 0, self.help_text + "\n", "")


class AnalyzerTests(unittest.TestCase):
    def analyze(self, root):
        return Analyzer(FakeRunner()).analyze(Path(root), probe_cli=True)

    def test_unmanaged_folder_recommends_init(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = self.analyze(directory)
            self.assertIn("ZED001", {item.code for item in snapshot.diagnostics})
            self.assertIn("zed-init", {action.id for action in snapshot.actions})

    def test_manifest_without_lock_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            snapshot = self.analyze(root)
            self.assertIn("ZED003", {item.code for item in snapshot.diagnostics})

    def test_stale_lock_and_missing_materialization_warn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / ".zpkg.lock"
            manifest = root / ".zpkg.toml"
            lock.write_text("version = 1\n", encoding="utf-8")
            old = time.time() - 20
            os.utime(lock, (old, old))
            manifest.write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n'
                '[dependencies]\n"acme/lib" = "^1"\n',
                encoding="utf-8",
            )
            snapshot = self.analyze(root)
            codes = {item.code for item in snapshot.diagnostics}
            self.assertIn("ZED004", codes)
            self.assertIn("ZED006", codes)

    def test_empty_lock_does_not_require_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            (root / ".zpkg.lock").write_text("version = 1\n", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertNotIn("ZED006", {item.code for item in snapshot.diagnostics})

    def test_dependency_manifest_requires_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n'
                '[dependencies]\n"acme/lib" = "^1"\n',
                encoding="utf-8",
            )
            (root / ".zpkg.lock").write_text("version = 1\n", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertIn("ZED006", {item.code for item in snapshot.diagnostics})

    def test_lock_only_uses_explicit_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.lock").write_text("version = 1\n", encoding="utf-8")
            snapshot = self.analyze(root)
            action = next(item for item in snapshot.actions if item.id == "zed-lock-only-restore")
            self.assertIn("--do-not-write-new-manifest", action.argv)

    def test_generated_consumer_manifest_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "zed-local"\nname = "demo"\nversion = "0.0.0"\n',
                encoding="utf-8",
            )
            snapshot = self.analyze(root)
            self.assertIn("ZED005", {item.code for item in snapshot.diagnostics})

    def test_invalid_toml_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text("[package\nname = 'x'\n", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertIn("ZED014", {item.code for item in snapshot.diagnostics})

    def test_invalid_lockfile_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            (root / ".zpkg.lock").write_text("[broken\n", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertIn("ZED016", {item.code for item in snapshot.diagnostics})

    def test_unknown_lock_schema_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            (root / ".zpkg.lock").write_text("version = 99\n", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertIn("ZED017", {item.code for item in snapshot.diagnostics})

    def test_interrupted_transaction_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zpkg.toml").write_text(
                '[package]\norg = "acme"\nname = "demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            staging = root / ".zpkg-staging" / "transaction"
            staging.mkdir(parents=True)
            (staging / "state.json").write_text("{}", encoding="utf-8")
            snapshot = self.analyze(root)
            self.assertIn("ZED007", {item.code for item in snapshot.diagnostics})
            self.assertEqual(snapshot.health.value, "error")

    def test_wrong_zed_binary_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Analyzer(FakeRunner(help_text="Zed editor command launcher")).analyze(
                Path(directory), probe_cli=True
            )
            self.assertIn("ZED011", {item.code for item in snapshot.diagnostics})


if __name__ == "__main__":
    unittest.main()
