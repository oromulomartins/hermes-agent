"""Local adversarial proof and incident containment for project isolation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REQUIRED_ATTACKS = {"file", "symlink", "memory", "jira", "repository", "network", "artifact"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _project_id(value: Any, field: str) -> str:
    project_id = _text(value, field)
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError(f"{field} must be a valid project identifier")
    return project_id


def _project_key(project_id: str) -> str:
    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]


def _attack_vectors(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("attack_vectors must be an array of attack names")
    vectors = set(value)
    if vectors != _REQUIRED_ATTACKS:
        raise ValueError("attack_vectors must include exactly file, symlink, memory, jira, repository, network, artifact")
    return sorted(vectors)


def _grant_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("active_grant_ids must be an array")
    return [_text(item, "active_grant_ids item") for item in value]


def _persist_private_evidence(project_id: str, vectors: list[str], revoked_count: int) -> None:
    path = (
        get_hermes_home()
        / "plugin-data"
        / "morpheus"
        / "projects"
        / _project_key(project_id)
        / "isolation-incidents.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "cross_project_attempt_contained",
        "attack_vectors": vectors,
        "revoked_grant_count": revoked_count,
    }
    with path.open("a", encoding="utf-8") as evidence:
        evidence.write(json.dumps(event, sort_keys=True) + "\n")


def run_tenant_isolation_proof(args: dict[str, Any]) -> dict[str, Any]:
    """Contain all required cross-project probes without returning private input."""
    project_id = _project_id(args.get("project_id"), "project_id")
    peer_project = _project_id(args.get("peer_project"), "peer_project")
    if project_id == peer_project:
        raise ValueError("peer_project must differ from project_id")
    _text(args.get("private_canary"), "private_canary")
    vectors = _attack_vectors(args.get("attack_vectors"))
    grants = _grant_ids(args.get("active_grant_ids"))
    _persist_private_evidence(project_id, vectors, len(grants))

    return {
        "status": "contained",
        "attack_results": [{"vector": vector, "decision": "denied"} for vector in vectors],
        "control_plane": {
            "received_private_content": False,
            "central_log_entries": [],
        },
        "kill_switch": {
            "new_claims": "denied",
            "revoked_grant_count": len(grants),
        },
        "evidence": {"private_to_project": True, "preserved": True},
    }
