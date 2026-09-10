"""Local, fail-closed project bindings for the Morpheus plugin."""

from __future__ import annotations

import hashlib
import re
from typing import Any


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_JIRA_PROJECT = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
_SECRET_REF = re.compile(r"^secret://[A-Za-z0-9._/-]+$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _project_id(value: Any, field: str) -> str:
    project_id = _text(value, field)
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError(f"{field} must contain only letters, numbers, dots, underscores, or hyphens")
    return project_id


def _secret_refs(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("secret_refs must be an object")
    result = {}
    for name, reference in value.items():
        key = _text(name, "secret_refs key")
        ref = _text(reference, f"secret_refs.{key}")
        if not _SECRET_REF.fullmatch(ref):
            raise ValueError(f"secret_refs.{key} must be a secret:// reference, not a credential value")
        result[key] = ref
    return result


def _binding_name(project_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_id.lower()).strip("-")
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:10]
    return f"morpheus-{slug}-{digest}"


def build_project_binding(args: dict[str, Any]) -> dict[str, Any]:
    """Build a local Docker binding after authenticating the requested project."""
    authenticated_project = _project_id(args.get("authenticated_project"), "authenticated_project")
    requested_project = _project_id(args.get("requested_project"), "requested_project")
    if requested_project != authenticated_project:
        raise PermissionError("requested project does not match authenticated project")

    repository = _text(args.get("repository"), "repository")
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use owner/name form")
    jira_project = _text(args.get("jira_project"), "jira_project")
    if not _JIRA_PROJECT.fullmatch(jira_project):
        raise ValueError("jira_project must be an uppercase Jira project key")
    runtime = _text(args.get("runtime", "docker-local"), "runtime")
    if runtime != "docker-local":
        raise ValueError("runtime must be docker-local for the current local-only rollout")

    binding_name = _binding_name(authenticated_project)
    return {
        "status": "ready",
        "binding": {
            "project_id": authenticated_project,
            "repository": repository,
            "jira_project": jira_project,
            "runtime": {
                "kind": runtime,
                "container_name": binding_name,
                "network": "none",
                "read_only_root_filesystem": True,
            },
            "storage": {
                "workspace": f"/opt/morpheus/projects/{binding_name}/workspace",
                "state": f"/opt/morpheus/projects/{binding_name}/state",
            },
            "secret_refs": _secret_refs(args.get("secret_refs")),
        },
        "policy": {
            "external_provisioning": False,
            "real_customer_data": False,
            "credentials_are_references_only": True,
        },
    }
