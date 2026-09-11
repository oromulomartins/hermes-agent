"""Fail-closed, project-scoped tool grants for the Morpheus plugin."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_JIRA_PROJECT = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
_TOOLS = {"github", "jira"}
_ACTIONS = {"read", "write"}
_POLICY_STATES = {"allow", "deny", "unavailable"}
_MAX_GRANT_SECONDS = 900


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _binding(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("binding must be an object")
    project_id = _text(value.get("project_id"), "binding.project_id")
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("binding.project_id must be a valid project identifier")
    repository = _text(value.get("repository"), "binding.repository")
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("binding.repository must use owner/name form")
    jira_project = _text(value.get("jira_project"), "binding.jira_project")
    if not _JIRA_PROJECT.fullmatch(jira_project):
        raise ValueError("binding.jira_project must be an uppercase Jira project key")
    return {"project_id": project_id, "repository": repository, "jira_project": jira_project}


def _project_key(project_id: str) -> str:
    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]


def _audit_denial(project_id: str, reason: str) -> None:
    path = (
        get_hermes_home()
        / "plugin-data"
        / "morpheus"
        / "projects"
        / _project_key(project_id)
        / "tool-broker-denials.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"event": "tool_access_denied", "project_id": project_id, "reason": reason}
    with path.open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(event, sort_keys=True) + "\n")


def _denied(project_id: str, reason: str) -> dict[str, Any]:
    _audit_denial(project_id, reason)
    return {
        "status": "denied",
        "reason": reason,
        "audit": {"event": "tool_access_denied", "recorded": True},
        "worker": {"credentials_available": False},
    }


def _now(value: Any) -> int:
    if value is None:
        return int(time.time())
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("now_epoch must be a non-negative integer")
    return value


def build_scoped_tool_grant(args: dict[str, Any]) -> dict[str, Any]:
    """Authorize one bound GitHub or Jira scope without exposing credentials."""
    binding = _binding(args.get("binding"))
    authenticated_project = _text(args.get("authenticated_project"), "authenticated_project")
    if authenticated_project != binding["project_id"]:
        return _denied(binding["project_id"], "principal_binding_mismatch")

    tool = _text(args.get("tool"), "tool")
    if tool not in _TOOLS:
        raise ValueError("tool must be github or jira")
    action = _text(args.get("action"), "action")
    if action not in _ACTIONS:
        raise ValueError("action must be read or write")
    policy_state = _text(args.get("policy_state", "allow"), "policy_state")
    if policy_state not in _POLICY_STATES:
        raise ValueError("policy_state must be allow, deny, or unavailable")
    if policy_state != "allow":
        return _denied(binding["project_id"], f"policy_{policy_state}")

    requested_scope = _text(args.get("requested_scope"), "requested_scope")
    authorized_scope = binding["repository"] if tool == "github" else binding["jira_project"]
    if requested_scope != authorized_scope:
        return _denied(binding["project_id"], "scope_not_authorized")

    now = _now(args.get("now_epoch"))
    expires_at = args.get("expires_at", now + _MAX_GRANT_SECONDS)
    if isinstance(expires_at, bool) or not isinstance(expires_at, int) or expires_at < 0:
        raise ValueError("expires_at must be a non-negative integer")
    if expires_at <= now:
        return _denied(binding["project_id"], "grant_expired")
    if expires_at - now > _MAX_GRANT_SECONDS:
        raise ValueError(f"grant duration must not exceed {_MAX_GRANT_SECONDS} seconds")

    scope = {"repository": authorized_scope} if tool == "github" else {"jira_project": authorized_scope}
    grant_id = hashlib.sha256(
        f"{binding['project_id']}:{tool}:{action}:{authorized_scope}:{expires_at}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "status": "granted",
        "grant": {
            "id": grant_id,
            "tool": tool,
            "action": action,
            "scope": scope,
            "expires_at": expires_at,
            "credential_material": "not_exposed",
        },
        "worker": {"credentials_available": False},
    }
