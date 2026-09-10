"""Behavioral coverage for the opt-in Morpheus plugin."""

from __future__ import annotations

import json

from hermes_cli.plugins import PluginManager
from tools.registry import registry


def _enable_morpheus_plugin(home):
    home.mkdir()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled:\n"
        "    - morpheus\n",
        encoding="utf-8",
    )


def test_morpheus_plugin_registers_namespaced_diagnostic_when_enabled(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    _enable_morpheus_plugin(home)
    monkeypatch.setenv("HERMES_HOME", str(home))

    manager = PluginManager()
    manager.discover_and_load()

    assert manager._plugins["morpheus"].enabled is True
    assert "morpheus-status" in manager._plugin_commands

    raw = registry.dispatch("morpheus_status", {}, scope=manager.scope_key)
    payload = json.loads(raw)

    assert payload["plugin"] == "morpheus"
    assert payload["capabilities"] == {
        "diagnostic": True,
        "scheduler": False,
        "worker": False,
        "kanban_adapter": "unconfigured",
    }


def test_morpheus_plugin_does_not_register_when_not_enabled(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))

    manager = PluginManager()
    manager.discover_and_load()

    assert "morpheus" not in {
        name for name, plugin in manager._plugins.items() if plugin.enabled
    }
    assert "morpheus_status" not in manager._plugin_tool_names
