"""Curated local routing for synthetic web-specialist tasks."""

from __future__ import annotations

import re
from typing import Any


_ROLES = {"Backend", "Frontend", "FullStack"}
_COORDINATOR_ROLES = {"PM", "PO", "TM", "TL"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _candidate(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("candidates must contain objects")
    candidate = {
        "name": _text(value.get("name"), "candidate.name"),
        "role": _text(value.get("role"), "candidate.role"),
        "adapter": _text(value.get("adapter"), "candidate.adapter"),
        "license": _text(value.get("license"), "candidate.license"),
        "sha": _text(value.get("sha"), "candidate.sha"),
        "digest": _text(value.get("digest"), "candidate.digest"),
    }
    if candidate["role"] not in _ROLES:
        raise ValueError("candidate.role must be Backend, Frontend, or FullStack")
    if not _SHA.fullmatch(candidate["sha"]) or not _SHA.fullmatch(candidate["digest"]):
        raise ValueError("candidate.sha and candidate.digest must be 64-character lowercase hexadecimal values")
    return candidate


def _candidates(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("candidates must be a non-empty array")
    candidates = [_candidate(item) for item in value]
    if len({item["name"] for item in candidates}) != len(candidates):
        raise ValueError("candidates must not contain duplicate names")
    return candidates


def route_curated_specialist(args: dict[str, Any]) -> dict[str, Any]:
    """Route one synthetic task to a metadata-complete local specialist entry."""
    project_id = _text(args.get("project_id"), "project_id")
    requested_role = _text(args.get("requested_role"), "requested_role")
    if requested_role not in _ROLES:
        raise ValueError("requested_role must be Backend, Frontend, or FullStack")
    coordinator_role = _text(args.get("coordinator_role"), "coordinator_role")
    if coordinator_role not in _COORDINATOR_ROLES:
        raise ValueError("coordinator_role must be PM, PO, TM, or TL")
    fixture = _text(args.get("fixture"), "fixture")
    candidates = _candidates(args.get("candidates"))
    selected = next((candidate for candidate in candidates if candidate["role"] == requested_role), None)
    if selected is None:
        return {
            "status": "needs_candidate",
            "requested_role": requested_role,
            "context": {"scope": "project_only", "global_client_context_available": False},
        }

    return {
        "status": "ready",
        "project_id": project_id,
        "specialist": selected,
        "validation": {
            "fixture": fixture,
            "output": {"role": requested_role, "adapter": selected["adapter"]},
            "valid": True,
            "executed": False,
        },
        "coordination": {
            "role": coordinator_role,
            "scope": "project_only",
            "global_client_context_available": False,
            "may_execute_specialist": False,
        },
    }
