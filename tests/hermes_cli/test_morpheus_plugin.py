"""Behavioral coverage for the opt-in Morpheus plugin."""

from __future__ import annotations

import json

import pytest

from hermes_cli.plugins import PluginManager
from plugins.morpheus.backlog import reconcile_backlog
from plugins.morpheus.spec import build_spec
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


def _ready_brief():
    return {
        "status": "ready",
        "pm_brief": {
            "target_user": "Online shoppers",
            "problem": "Buyers lack timely delivery visibility.",
        },
        "po_brief": {
            "value_hypothesis": "Fewer support requests about delivery status.",
        },
    }


def _spec_args():
    return {
        "brief": _ready_brief(),
        "decision": {"id": "DEC-1", "owner": "PO", "state": "approved"},
        "behavior": "Show a delivery lifecycle state for a selected order.",
        "public_test_limits": "Use synthetic order and shipment identifiers only.",
        "skill_lock": {
            "name": "matt-jira",
            "revision": "2026-09-10",
            "adaptations": ["Jira cards are the delivery tracker."],
        },
        "slices": [
            {
                "id": "delivery-read",
                "title": "Read delivery state",
                "value": "Buyer sees shipment progress",
                "acceptance": "Synthetic order returns its lifecycle state",
                "blockers": "None",
                "depends_on": [],
            },
            {
                "id": "delivery-view",
                "title": "Display delivery state",
                "value": "Buyer can understand shipment progress",
                "acceptance": "Lifecycle state is visible in the order view",
                "blockers": "delivery-read",
                "depends_on": ["delivery-read"],
            },
        ],
    }


def test_morpheus_plugin_registers_namespaced_diagnostic_when_enabled(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    assert manager._plugins["morpheus"].enabled is True
    assert "morpheus-status" in manager._plugin_commands

    raw = registry.dispatch("morpheus_status", {}, scope=manager.scope_key)
    payload = json.loads(raw)

    assert payload["plugin"] == "morpheus"
    assert payload["capabilities"]["spec_slices"] is True
    assert payload["capabilities"]["backlog_reconcile"] is True


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


def test_morpheus_spec_requires_explicit_approval():
    result = build_spec({**_spec_args(), "decision": {"id": "DEC-1", "owner": "PO", "state": "pending"}})

    assert result["status"] == "needs_decision"
    assert result["decisions"][0]["state"] == "needs_input"


def test_morpheus_spec_builds_an_acyclic_vertical_slice_dag(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch("morpheus_spec_slices", _spec_args(), scope=manager.scope_key)
    result = json.loads(raw)

    assert result["status"] == "ready"
    assert result["spec"]["execution_order"] == ["delivery-read", "delivery-view"]
    assert result["spec"]["decisions"] == [{"id": "DEC-1", "owner": "PO", "state": "approved"}]
    assert result["spec"]["skill_lock"]["name"] == "matt-jira"


def test_morpheus_spec_rejects_a_cyclic_slice_graph():
    args = _spec_args()
    args["slices"][0]["depends_on"] = ["delivery-view"]

    with pytest.raises(ValueError, match="acyclic"):
        build_spec(args)


def test_morpheus_plugin_does_not_register_when_not_enabled(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))

    manager = PluginManager()
    manager.discover_and_load()

    assert "morpheus" not in {name for name, plugin in manager._plugins.items() if plugin.enabled}
    assert "morpheus_status" not in manager._plugin_tool_names
    assert "morpheus_intake_brief" not in manager._plugin_tool_names
    assert "morpheus_spec_slices" not in manager._plugin_tool_names


def _backlog_items():
    return [
        {
            "source_id": "MP-001",
            "issue_type": "Task",
            "summary": "Bootstrap Morpheus",
            "depends_on": [],
        },
        {
            "source_id": "MP-002",
            "issue_type": "Story",
            "summary": "Enable Morpheus",
            "parent_source_id": "MP-001",
            "depends_on": ["MP-001"],
        },
    ]


def test_morpheus_backlog_reconciliation_is_idempotent(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    args = {
        "bound_project": "BPT",
        "project": "BPT",
        "items": _backlog_items(),
        "existing_items": [{"source_id": "MP-001", "issue_key": "BPT-9", "summary": "Bootstrap Morpheus"}],
    }

    first = json.loads(registry.dispatch("morpheus_backlog_reconcile", args, scope=manager.scope_key))
    repeated = reconcile_backlog({**args, "existing_items": [
        {"source_id": "MP-001", "issue_key": "BPT-9", "summary": "Bootstrap Morpheus"},
        {"source_id": "MP-002", "issue_key": "BPT-10", "summary": "Enable Morpheus"},
    ]})

    assert [item["source_id"] for item in first["create"]] == ["MP-002"]
    assert first["unchanged"] == [{"source_id": "MP-001", "issue_key": "BPT-9"}]
    assert repeated["create"] == []
    assert {item["issue_key"] for item in repeated["unchanged"]} == {"BPT-9", "BPT-10"}


def test_morpheus_backlog_reconciliation_rejects_project_outside_binding():
    with pytest.raises(PermissionError, match="outside the configured binding"):
        reconcile_backlog({
            "bound_project": "BPT",
            "project": "OTHER",
            "items": _backlog_items(),
        })


def test_morpheus_backlog_reconciliation_rejects_duplicate_source_ids():
    with pytest.raises(ValueError, match="duplicate source_id"):
        reconcile_backlog({
            "bound_project": "BPT",
            "project": "BPT",
            "items": [_backlog_items()[0], _backlog_items()[0]],
        })
