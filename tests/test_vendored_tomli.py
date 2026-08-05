import subprocess
import sys
import unittest

from zed_pkg_insights._vendor import tomli


class VendoredTomliTests(unittest.TestCase):
    def test_parses_zed_manifest_shapes(self):
        value = tomli.loads(
            '[package]\n'
            'org = "acme"\n'
            'name = "demo"\n'
            'version = "0.1.0"\n'
            '[dependencies]\n'
            '"acme/lib" = "^1"\n'
            '[install]\n'
            'dir = ".vendor/.zed"\n'
        )
        self.assertEqual(value["package"]["org"], "acme")
        self.assertEqual(value["dependencies"]["acme/lib"], "^1")
        self.assertEqual(value["install"]["dir"], ".vendor/.zed")

    def test_exposes_decode_error_location(self):
        with self.assertRaises(tomli.TOMLDecodeError) as context:
            tomli.loads("[package\nname = 'x'\n")
        self.assertEqual(context.exception.lineno, 1)

    def test_analyzer_falls_back_when_tomllib_is_unavailable(self):
        script = r'''
import builtins
real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "tomllib":
        raise ImportError("simulated Python 3.8 runtime")
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
from zed_pkg_insights import analyzer
assert analyzer.tomllib.__version__ == "2.2.1"
'''
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
