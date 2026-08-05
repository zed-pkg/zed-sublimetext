import importlib
import sys
import types
import unittest


class PluginImportTests(unittest.TestCase):
    def test_plugin_module_imports_with_sublime_stubs(self):
        sublime = types.ModuleType("sublime")
        sublime.windows = lambda: []
        sublime_plugin = types.ModuleType("sublime_plugin")
        sublime_plugin.WindowCommand = type("WindowCommand", (), {})
        sublime_plugin.EventListener = type("EventListener", (), {})
        previous_sublime = sys.modules.get("sublime")
        previous_plugin = sys.modules.get("sublime_plugin")
        sys.modules["sublime"] = sublime
        sys.modules["sublime_plugin"] = sublime_plugin
        try:
            module = importlib.import_module("zed_sublimetext")
            self.assertTrue(hasattr(module, "ZedPackageInsightsRefreshCommand"))
            self.assertTrue(hasattr(module, "ZedPackageInsightsEventListener"))
        finally:
            sys.modules.pop("zed_sublimetext", None)
            if previous_sublime is None:
                sys.modules.pop("sublime", None)
            else:
                sys.modules["sublime"] = previous_sublime
            if previous_plugin is None:
                sys.modules.pop("sublime_plugin", None)
            else:
                sys.modules["sublime_plugin"] = previous_plugin


if __name__ == "__main__":
    unittest.main()
