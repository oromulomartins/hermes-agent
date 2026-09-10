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


def _enabled_manager(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    _enable_morpheus_plugin(home)
    monkeypatch.setenv("HERMES_HOME", str(home))
    manager = PluginManager()
    manager.discover_and_load()
    return manager


def test_morpheus_plugin_registers_namespaced_diagnostic_when_enabled(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    assert manager._plugins["morpheus"].enabled is True
    assert "morpheus-status" in manager._plugin_commands

    raw = registry.dispatch("morpheus_status", {}, scope=manager.scope_key)
    payload = json.loads(raw)

    assert payload["plugin"] == "morpheus"
    assert payload["capabilities"] == {
        "diagnostic": True,
        "intake_brief": True,
        "scheduler": False,
        "worker": False,
        "kanban_adapter": "unconfigured",
    }


def test_morpheus_intake_produces_separate_briefs_and_persists_glossary(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch(
        "morpheus_intake_brief",
        {
            "project": "Synthetic Commerce",
            "demand": "Help buyers track the status of a delivery.",
            "target_user": "Online shoppers",
            "problem": "Buyers lack timely delivery visibility.",
            "value_hypothesis": "Fewer support requests about delivery status.",
            "constraints": ["Use synthetic data only."],
            "terms": {"delivery status": "Current lifecycle state of an order shipment."},
        },
        scope=manager.scope_key,
    )
    brief = json.loads(raw)

    assert brief["status"] == "ready"
    assert brief["pm_brief"]["target_user"] == "Online shoppers"
    assert brief["po_brief"]["value_hypothesis"] == "Fewer support requests about delivery status."
    assert brief["questions"] == []
    assert brief["glossary"]["delivery status"] == "Current lifecycle state of an order shipment."


def test_morpheus_intake_marks_missing_information_as_needs_input(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch(
        "morpheus_intake_brief",
        {"project": "Synthetic Commerce", "demand": "Improve the buying experience."},
        scope=manager.scope_key,
    )
    brief = json.loads(raw)

    assert brief["status"] == "needs_input"
    assert {question["field"] for question in brief["questions"]} == {
        "target_user",
        "problem",
        "value_hypothesis",
    }
    assert {question["owner"] for question in brief["pm_brief"]["open_questions"]} == {"PM"}
    assert {question["owner"] for question in brief["po_brief"]["open_questions"]} == {"PO"}


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
    assert "morpheus_intake_brief" not in manager._plugin_tool_names
