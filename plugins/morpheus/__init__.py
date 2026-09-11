"""Opt-in Morpheus plugin for Hermes Agent.

The plugin exposes namespaced workflow surfaces. Discovery never starts workers,
schedules, or external integrations.
"""

from __future__ import annotations

import json
from typing import Any

from .backlog import reconcile_backlog
from .binding import build_project_binding
from .broker import build_scoped_tool_grant
from .intake import build_intake_brief
from .isolation import run_tenant_isolation_proof
from .memory import build_private_memory
from .onboarding import build_repository_onboarding
from .spec import build_spec
from .specialists import route_curated_specialist
from .supervisor import manage_durable_run
from .worker import build_isolated_worker


_DIAGNOSTIC_TOOL_NAME = "morpheus_status"
_DIAGNOSTIC_COMMAND_NAME = "morpheus-status"
_INTAKE_TOOL_NAME = "morpheus_intake_brief"
_SPEC_TOOL_NAME = "morpheus_spec_slices"
_BACKLOG_TOOL_NAME = "morpheus_backlog_reconcile"
_PROJECT_BINDING_TOOL_NAME = "morpheus_project_binding"
_ISOLATED_WORKER_TOOL_NAME = "morpheus_isolated_worker"
_PRIVATE_MEMORY_TOOL_NAME = "morpheus_project_memory"
_SCOPED_TOOL_GRANT_NAME = "morpheus_scoped_tool_grant"
_REPOSITORY_ONBOARDING_TOOL_NAME = "morpheus_repository_onboarding"
_TENANT_ISOLATION_PROOF_TOOL_NAME = "morpheus_tenant_isolation_proof"
_DURABLE_RUN_TOOL_NAME = "morpheus_durable_run"
_CURATED_SPECIALIST_TOOL_NAME = "morpheus_curated_specialist"


def _status_payload() -> dict[str, Any]:
    return {
        "plugin": "morpheus",
        "enabled": True,
        "capabilities": {
            "diagnostic": True,
            "intake_brief": True,
            "spec_slices": True,
            "backlog_reconcile": True,
            "project_binding": True,
            "isolated_worker_plan": True,
            "private_project_memory": True,
            "scoped_tool_grant": True,
            "repository_onboarding": True,
            "tenant_isolation_proof": True,
            "durable_run_supervisor": True,
            "curated_web_specialists": True,
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


def _backlog_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(reconcile_backlog(args), sort_keys=True)


def _project_binding_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_project_binding(args), sort_keys=True)


def _isolated_worker_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_isolated_worker(args), sort_keys=True)


def _private_memory_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_private_memory(args), sort_keys=True)


def _scoped_tool_grant(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_scoped_tool_grant(args), sort_keys=True)


def _repository_onboarding_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(build_repository_onboarding(args), sort_keys=True)


def _tenant_isolation_proof_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(run_tenant_isolation_proof(args), sort_keys=True)


def _durable_run_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(manage_durable_run(args), sort_keys=True)


def _curated_specialist_tool(args: dict[str, Any], **__: Any) -> str:
    return json.dumps(route_curated_specialist(args), sort_keys=True)


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
    ctx.register_tool(
        name=_BACKLOG_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _BACKLOG_TOOL_NAME,
            "description": (
                "Plan an idempotent backlog reconciliation within one bound Jira project "
                "without performing remote writes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bound_project": {"type": "string"},
                    "project": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "object"}},
                    "existing_items": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["bound_project", "project", "items"],
                "additionalProperties": False,
            },
        },
        handler=_backlog_tool,
        description="Morpheus idempotent backlog reconciliation planner.",
    )
    ctx.register_tool(
        name=_PROJECT_BINDING_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _PROJECT_BINDING_TOOL_NAME,
            "description": (
                "Build a fail-closed local Docker project binding. The requested "
                "project must match the authenticated project, and secrets are references only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "authenticated_project": {"type": "string"},
                    "requested_project": {"type": "string"},
                    "repository": {"type": "string"},
                    "jira_project": {"type": "string"},
                    "runtime": {"type": "string", "enum": ["docker-local"]},
                    "secret_refs": {"type": "object", "additionalProperties": {"type": "string"}},
                },
                "required": ["authenticated_project", "requested_project", "repository", "jira_project"],
                "additionalProperties": False,
            },
        },
        handler=_project_binding_tool,
        description="Morpheus local Docker project-binding contract.",
    )
    ctx.register_tool(
        name=_ISOLATED_WORKER_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _ISOLATED_WORKER_TOOL_NAME,
            "description": (
                "Build a fail-closed plan for a disposable local Docker worker. "
                "It does not start a container or expose credentials."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "authenticated_project": {"type": "string"},
                    "binding": {"type": "object"},
                    "run_id": {"type": "string"},
                },
                "required": ["authenticated_project", "binding", "run_id"],
                "additionalProperties": False,
            },
        },
        handler=_isolated_worker_tool,
        description="Morpheus disposable local Docker worker plan.",
    )
    ctx.register_tool(
        name=_PRIVATE_MEMORY_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _PRIVATE_MEMORY_TOOL_NAME,
            "description": (
                "Persist or retrieve private memory and handoff artifacts for one "
                "authenticated project. No cross-project search is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "authenticated_project": {"type": "string"},
                    "binding": {"type": "object"},
                    "operation": {"type": "string", "enum": ["append", "read"]},
                    "writer_id": {"type": "string"},
                    "record": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["memory", "handoff"]},
                            "summary": {"type": "string"},
                            "artifact_refs": {"type": "array", "items": {"type": "string"}},
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["authenticated_project", "binding", "operation"],
                "additionalProperties": False,
            },
        },
        handler=_private_memory_tool,
        description="Morpheus project-bound private memory and handoff store.",
    )
    ctx.register_tool(
        name=_SCOPED_TOOL_GRANT_NAME,
        toolset="debugging",
        schema={
            "name": _SCOPED_TOOL_GRANT_NAME,
            "description": (
                "Issue a short-lived, project-scoped GitHub or Jira grant without "
                "exposing credential material to a worker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "authenticated_project": {"type": "string"},
                    "binding": {"type": "object"},
                    "tool": {"type": "string", "enum": ["github", "jira"]},
                    "action": {"type": "string", "enum": ["read", "write"]},
                    "requested_scope": {"type": "string"},
                    "policy_state": {"type": "string", "enum": ["allow", "deny", "unavailable"]},
                    "now_epoch": {"type": "integer", "minimum": 0},
                    "expires_at": {"type": "integer", "minimum": 0},
                },
                "required": ["authenticated_project", "binding", "tool", "action", "requested_scope"],
                "additionalProperties": False,
            },
        },
        handler=_scoped_tool_grant,
        description="Morpheus fail-closed, project-scoped tool grant broker.",
    )
    ctx.register_tool(
        name=_REPOSITORY_ONBOARDING_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _REPOSITORY_ONBOARDING_TOOL_NAME,
            "description": (
                "Inventory a received repository and return a curated mount plan "
                "without executing discovered hooks, plugins, MCPs, or scripts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source_repository": {"type": "string"},
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                            "required": ["path", "content"],
                            "additionalProperties": False,
                        },
                    },
                    "approved_capabilities": {"type": "array", "items": {"type": "string"}},
                    "curated_extensions": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["source_repository", "files", "approved_capabilities"],
                "additionalProperties": False,
            },
        },
        handler=_repository_onboarding_tool,
        description="Morpheus declarative, quarantine-first repository onboarding.",
    )
    ctx.register_tool(
        name=_TENANT_ISOLATION_PROOF_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _TENANT_ISOLATION_PROOF_TOOL_NAME,
            "description": (
                "Run a local, deterministic cross-project isolation proof and apply "
                "a project kill switch without exposing private test content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "peer_project": {"type": "string"},
                    "private_canary": {"type": "string"},
                    "attack_vectors": {"type": "array", "items": {"type": "string"}},
                    "active_grant_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_id", "peer_project", "private_canary", "attack_vectors"],
                "additionalProperties": False,
            },
        },
        handler=_tenant_isolation_proof_tool,
        description="Morpheus local project-isolation proof and kill switch.",
    )
    ctx.register_tool(
        name=_DURABLE_RUN_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _DURABLE_RUN_TOOL_NAME,
            "description": "Manage local durable claims, fencing, heartbeats, and checkpoints without starting a worker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["claim", "heartbeat", "checkpoint", "publish", "resume"]},
                    "project_id": {"type": "string"},
                    "repository": {"type": "string"},
                    "task_id": {"type": "string"},
                    "worker_id": {"type": "string"},
                    "now_epoch": {"type": "integer", "minimum": 0},
                    "lease_seconds": {"type": "integer", "minimum": 0},
                    "fencing_token": {"type": "integer", "minimum": 0},
                    "spec_sha": {"type": "string"},
                    "head_sha": {"type": "string"},
                },
                "required": ["operation", "project_id", "repository", "task_id", "worker_id", "now_epoch"],
                "additionalProperties": False,
            },
        },
        handler=_durable_run_tool,
        description="Morpheus local durable-run claim and checkpoint supervisor.",
    )
    ctx.register_tool(
        name=_CURATED_SPECIALIST_TOOL_NAME,
        toolset="debugging",
        schema={
            "name": _CURATED_SPECIALIST_TOOL_NAME,
            "description": "Route a synthetic web task to a locally curated, metadata-complete specialist without executing external code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "requested_role": {"type": "string", "enum": ["Backend", "Frontend", "FullStack"]},
                    "coordinator_role": {"type": "string", "enum": ["PM", "PO", "TM", "TL"]},
                    "fixture": {"type": "string"},
                    "candidates": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["project_id", "requested_role", "coordinator_role", "fixture", "candidates"],
                "additionalProperties": False,
            },
        },
        handler=_curated_specialist_tool,
        description="Morpheus curated Backend, Frontend, and FullStack specialist router.",
    )
    ctx.register_command(
        _DIAGNOSTIC_COMMAND_NAME,
        _diagnostic_command,
        description="Show Morpheus plugin capability status.",
    )
