"""Opt-in Morpheus plugin for Hermes Agent.

The plugin exposes namespaced workflow surfaces. Discovery never starts workers,
schedules, or external integrations.
"""

from __future__ import annotations

import json
from typing import Any

from .intake import build_intake_brief
from .spec import build_spec


_DIAGNOSTIC_TOOL_NAME = "morpheus_status"
_DIAGNOSTIC_COMMAND_NAME = "morpheus-status"
_INTAKE_TOOL_NAME = "morpheus_intake_brief"
_SPEC_TOOL_NAME = "morpheus_spec_slices"


def _status_payload() -> dict[str, Any]:
    return {
        "plugin": "morpheus",
        "enabled": True,
        "capabilities": {
            "diagnostic": True,
            "intake_brief": True,
            "spec_slices": True,
            "scheduler": False,
            "worker": False,
            "kanban_adapter": "unconfigured",
        },
        "message": (
            "Morpheus is enabled in diagnostic-only mode. No worker or "
            "scheduled job has been started."
        ),
    }


def _diagnostic_tool(_: dict[str, Any], **__: Any) -> str:
    return json.dumps(_status_payload(), sort_keys=True)


def _diagnostic_command(_: str) -> str:
    payload = _status_payload()
    return (
        "Morpheus status: diagnostic-only; no worker or scheduled job is "
        f"running (kanban adapter: {payload['capabilities']['kanban_adapter']})."
    )


def _intake_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_intake_brief(args), sort_keys=True)


def _spec_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_spec(args), sort_keys=True)


def register(ctx: Any) -> None:
    ctx.register_tool(
        name=_DIAGNOSTIC_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _DIAGNOSTIC_TOOL_NAME,
            "description": "Report the enabled Morpheus plugin capabilities without starting work.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        handler=_diagnostic_tool,
        description="Morpheus compatibility and capability diagnostic.",
    )
    ctx.register_tool(
        name=_INTAKE_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _INTAKE_TOOL_NAME,
            "description": (
                "Create deterministic PM and PO intake briefs. Missing information "
                "becomes explicit needs_input questions instead of inferred requirements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "demand": {"type": "string"},
                    "target_user": {"type": "string"},
                    "problem": {"type": "string"},
                    "value_hypothesis": {"type": "string"},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "terms": {"type": "object", "additionalProperties": {"type": "string"}},
                },
                "required": ["project", "demand"],
                "additionalProperties": False,
            },
        },
        handler=_intake_tool,
        description="Morpheus deterministic intake brief generator.",
    )
    ctx.register_tool(
        name=_SPEC_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _SPEC_TOOL_NAME,
            "description": (
                "Convert an explicitly approved intake brief into a traceable spec "
                "and acyclic vertical slices."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brief": {"type": "object"},
                    "decision": {"type": "object"},
                    "behavior": {"type": "string"},
                    "public_test_limits": {"type": "string"},
                    "skill_lock": {"type": "object"},
                    "slices": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["brief", "decision", "behavior", "public_test_limits", "skill_lock", "slices"],
                "additionalProperties": False,
            },
        },
        handler=_spec_tool,
        description="Morpheus approved-brief spec and slice DAG generator.",
    )
    ctx.register_command(
        _DIAGNOSTIC_COMMAND_NAME,
        _diagnostic_command,
        description="Show Morpheus plugin capability status.",
    )
