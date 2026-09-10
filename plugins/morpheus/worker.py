"""Fail-closed plans for disposable local Docker workers."""

from __future__ import annotations

import re
from typing import Any


_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _binding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("binding must be an object")
    project_id = _text(value.get("project_id"), "binding.project_id")
    runtime = value.get("runtime")
    storage = value.get("storage")
    if not isinstance(runtime, dict) or runtime.get("kind") != "docker-local":
        raise ValueError("binding.runtime.kind must be docker-local")
    if not isinstance(storage, dict):
        raise ValueError("binding.storage must be an object")
    return {
        "project_id": project_id,
        "container_name": _text(runtime.get("container_name"), "binding.runtime.container_name"),
        "workspace": _text(storage.get("workspace"), "binding.storage.workspace"),
        "state": _text(storage.get("state"), "binding.storage.state"),
    }


def build_isolated_worker(args: dict[str, Any]) -> dict[str, Any]:
    """Build a non-executing Docker worker plan for one authenticated project."""
    binding = _binding(args.get("binding"))
    authenticated_project = _text(args.get("authenticated_project"), "authenticated_project")
    if binding["project_id"] != authenticated_project:
        raise PermissionError("worker binding does not match authenticated project")
    run_id = _text(args.get("run_id"), "run_id")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must contain only letters, numbers, underscores, or hyphens")

    run_root = f"{binding['state']}/runs/{run_id}"
    return {
        "status": "ready",
        "worker": {
            "container_name": f"{binding['container_name']}-run-{run_id}",
            "image": "python:3.13-slim",
            "user": "65532:65532",
            "network": "none",
            "read_only_root_filesystem": True,
            "privileged": False,
            "docker_socket": False,
            "drop_capabilities": ["ALL"],
            "no_new_privileges": True,
            "mounts": [
                {"source": binding["workspace"], "target": "/workspace", "read_only": False},
                {"source": f"{run_root}/home", "target": "/home/worker", "read_only": False},
            ],
            "tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},
        },
        "cleanup": {
            "remove_container": True,
            "remove_run_home": f"{run_root}/home",
            "retain_authenticated_cache": False,
        },
    }
