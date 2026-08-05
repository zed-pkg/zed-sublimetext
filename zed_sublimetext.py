from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

import sublime
import sublime_plugin

try:
    from .zed_pkg_insights.analyzer import Analyzer
    from .zed_pkg_insights.model import Action, ActionKind, Snapshot
    from .zed_pkg_insights.presentation import render_snapshot
    from .zed_pkg_insights.project import find_project_root
    from .zed_pkg_insights.runner import CommandRunner
except ImportError:  # Makes local syntax tooling happier outside Sublime.
    from zed_pkg_insights.analyzer import Analyzer
    from zed_pkg_insights.model import Action, ActionKind, Snapshot
    from zed_pkg_insights.presentation import render_snapshot
    from zed_pkg_insights.project import find_project_root
    from zed_pkg_insights.runner import CommandRunner

SETTINGS_FILE = "ZedPackageInsights.sublime-settings"
OUTPUT_PANEL = "zed_package_insights"
STATUS_KEY = "zed_package_insights"

_snapshots: Dict[int, Snapshot] = {}
_refresh_generations: Dict[int, int] = {}
_lock = threading.Lock()


def plugin_loaded() -> None:
    for window in sublime.windows():
        _schedule_refresh(window, show=False, delay_ms=250)


class ZedPackageInsightsRefreshCommand(sublime_plugin.WindowCommand):
    def run(self, show: bool = True) -> None:
        _schedule_refresh(self.window, show=show, delay_ms=0)


class ZedPackageInsightsShowCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        snapshot = _snapshots.get(self.window.id())
        if snapshot is None:
            _schedule_refresh(self.window, show=True, delay_ms=0)
            return
        _show_snapshot(self.window, snapshot)


class ZedPackageInsightsActionsCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        snapshot = _snapshots.get(self.window.id())
        if snapshot is None:
            _schedule_refresh(self.window, show=False, delay_ms=0, then_actions=True)
            return
        _show_actions(self.window, snapshot)


class ZedPackageInsightsOpenSettingsCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        self.window.run_command(
            "edit_settings",
            {"base_file": "${packages}/ZedPackageInsights/{0}".format(SETTINGS_FILE)},
        )


class ZedPackageInsightsEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view: sublime.View) -> None:
        _refresh_for_view(view, delay_ms=500)

    def on_activated_async(self, view: sublime.View) -> None:
        _refresh_for_view(view, delay_ms=500)

    def on_post_save_async(self, view: sublime.View) -> None:
        file_name = view.file_name()
        if file_name and Path(file_name).name in (".zpkg.toml", ".zpkg.lock"):
            _refresh_for_view(view, delay_ms=150)


def _refresh_for_view(view: sublime.View, delay_ms: int) -> None:
    settings = sublime.load_settings(SETTINGS_FILE)
    if not settings.get("auto_refresh", True):
        return
    window = view.window()
    if window is not None:
        _schedule_refresh(window, show=False, delay_ms=delay_ms)


def _schedule_refresh(
    window: sublime.Window,
    show: bool,
    delay_ms: int,
    then_actions: bool = False,
) -> None:
    window_id = window.id()
    with _lock:
        generation = _refresh_generations.get(window_id, 0) + 1
        _refresh_generations[window_id] = generation

    def dispatch() -> None:
        with _lock:
            if _refresh_generations.get(window_id) != generation:
                return
        sublime.set_timeout_async(
            lambda: _perform_refresh(window, generation, show, then_actions), 0
        )

    sublime.set_timeout(dispatch, delay_ms)


def _perform_refresh(
    window: sublime.Window,
    generation: int,
    show: bool,
    then_actions: bool,
) -> None:
    settings = sublime.load_settings(SETTINGS_FILE)
    root = _resolve_root(window)
    analyzer = Analyzer()
    snapshot = analyzer.analyze(
        root=root,
        zed_binary=settings.get("zed_binary", "zed"),
        probe_cli=settings.get("probe_cli_on_refresh", True),
        command_timeout_seconds=float(settings.get("command_timeout_seconds", 8.0)),
    )

    def complete() -> None:
        with _lock:
            if _refresh_generations.get(window.id()) != generation:
                return
            _snapshots[window.id()] = snapshot
        _update_status(window, snapshot)
        if show:
            _show_snapshot(window, snapshot)
        if then_actions:
            _show_actions(window, snapshot)

    sublime.set_timeout(complete, 0)


def _resolve_root(window: sublime.Window) -> Path:
    folders = [Path(folder) for folder in window.folders()]
    active = window.active_view()
    if active is not None and active.file_name():
        start = Path(active.file_name())
    elif folders:
        start = folders[0]
    else:
        start = Path.home()
    return find_project_root(start, folders)


def _show_snapshot(window: sublime.Window, snapshot: Snapshot) -> None:
    panel = window.create_output_panel(OUTPUT_PANEL)
    panel.set_read_only(False)
    panel.run_command("select_all")
    panel.run_command("right_delete")
    panel.run_command(
        "append",
        {"characters": render_snapshot(snapshot), "force": True, "scroll_to_end": False},
    )
    panel.set_read_only(True)
    window.run_command("show_panel", {"panel": "output.{0}".format(OUTPUT_PANEL)})


def _show_actions(window: sublime.Window, snapshot: Snapshot) -> None:
    actions = snapshot.actions
    if not actions:
        sublime.status_message("Zed Package Insights: no recommended actions")
        return
    items = [[action.title, action.description or action.display_command()] for action in actions]

    def selected(index: int) -> None:
        if index >= 0:
            _apply_action(window, snapshot, actions[index])

    window.show_quick_panel(items, selected)


def _apply_action(window: sublime.Window, snapshot: Snapshot, action: Action) -> None:
    if action.kind == ActionKind.OPEN_FILE and action.path is not None:
        encoded = str(action.path)
        window.open_file(encoded)
        return
    if action.kind == ActionKind.OPEN_SETTINGS:
        window.run_command("zed_package_insights_open_settings")
        return
    if action.kind == ActionKind.COPY_COMMAND:
        sublime.set_clipboard(action.display_command())
        sublime.status_message("Copied: {0}".format(action.display_command()))
        return
    if action.kind != ActionKind.RUN_ZED:
        sublime.error_message("Unsupported Zed Package Insights action")
        return

    if action.requires_confirmation:
        approved = sublime.ok_cancel_dialog(
            "Run this command in {0}?\n\n{1}\n\nThe plugin never runs recommended fixes without confirmation.".format(
                snapshot.root, action.display_command()
            ),
            "Run Command",
        )
        if not approved:
            return

    settings = sublime.load_settings(SETTINGS_FILE)
    timeout = float(settings.get("action_timeout_seconds", 120.0))
    sublime.status_message("Zed Package Insights: running {0}".format(action.display_command()))

    def execute() -> None:
        result = CommandRunner().run(action.argv, snapshot.root, timeout)
        output = [
            "$ {0}".format(action.display_command()),
            "exit: {0}".format(result.returncode),
            "",
            result.stdout.rstrip(),
        ]
        if result.stderr.strip():
            output.extend(["", "stderr:", result.stderr.rstrip()])
        text = "\n".join(output).rstrip() + "\n"

        def complete() -> None:
            panel = window.create_output_panel(OUTPUT_PANEL)
            panel.set_read_only(False)
            panel.run_command("select_all")
            panel.run_command("right_delete")
            panel.run_command("append", {"characters": text, "force": True})
            panel.set_read_only(True)
            window.run_command("show_panel", {"panel": "output.{0}".format(OUTPUT_PANEL)})
            _schedule_refresh(window, show=False, delay_ms=250)

        sublime.set_timeout(complete, 0)

    sublime.set_timeout_async(execute, 0)


def _update_status(window: sublime.Window, snapshot: Snapshot) -> None:
    active = window.active_view()
    if active is not None:
        active.set_status(STATUS_KEY, snapshot.status_text())
