"""Opt-in Morpheus plugin for Hermes Agent.

The plugin only exposes a namespaced diagnostic surface. It does not start
workers, schedules, or external integrations during discovery.
"""

from __future__ import annotations

import json
from typing import Any


_DIAGNOSTIC_TOOL_NAME = "morpheus_status"
_DIAGNOSTIC_COMMAND_NAME = "morpheus-status"


def _status_payload() -> dict[str, Any]:
    return {
        "plugin": "morpheus",
        "enabled": True,
        "capabilities": {
            "diagnostic": True,
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


def register(ctx: Any) -> None:
    ctx.register_tool(
        name=_DIAGNOSTIC_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _DIAGNOSTIC_TOOL_NAME,
            "description": "Report the enabled Morpheus plugin capabilities without starting work.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        handler=_diagnostic_tool,
        description="Morpheus compatibility and capability diagnostic.",
    )
    ctx.register_command(
        _DIAGNOSTIC_COMMAND_NAME,
        _diagnostic_command,
        description="Show Morpheus plugin capability status.",
    )
