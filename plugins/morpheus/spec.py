"""Spec assembly and DAG validation for the Morpheus plugin."""

from __future__ import annotations

from collections import deque
from typing import Any


_SLICE_FIELDS = ("id", "title", "value", "acceptance", "blockers")


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _approval(decision: Any) -> dict[str, str] | None:
    if not isinstance(decision, dict):
        return None
    decision_id = decision.get("id")
    owner = decision.get("owner")
    state = decision.get("state")
    if not all(isinstance(value, str) and value.strip() for value in (decision_id, owner, state)):
        return None
    return {"id": decision_id.strip(), "owner": owner.strip(), "state": state.strip()}


def _skill_lock(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("skill_lock must be an object")
    name = _non_empty_string(value.get("name"), "skill_lock.name")
    revision = _non_empty_string(value.get("revision"), "skill_lock.revision")
    adaptations = value.get("adaptations")
    if not isinstance(adaptations, list) or any(not isinstance(item, str) or not item.strip() for item in adaptations):
        raise ValueError("skill_lock.adaptations must be an array of non-empty strings")
    return {"name": name, "revision": revision, "adaptations": [item.strip() for item in adaptations]}


def _slices(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("slices must be a non-empty array")
    result = []
    ids = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each slice must be an object")
        slice_data = {field: _non_empty_string(item.get(field), f"slice.{field}") for field in _SLICE_FIELDS}
        depends_on = item.get("depends_on", [])
        if not isinstance(depends_on, list) or any(not isinstance(dep, str) or not dep.strip() for dep in depends_on):
            raise ValueError("slice.depends_on must be an array of non-empty strings")
        if slice_data["id"] in ids:
            raise ValueError(f"duplicate slice id: {slice_data['id']}")
        ids.add(slice_data["id"])
        slice_data["depends_on"] = [dep.strip() for dep in depends_on]
        result.append(slice_data)
    unknown = {dep for item in result for dep in item["depends_on"] if dep not in ids}
    if unknown:
        raise ValueError(f"slice dependencies reference unknown ids: {', '.join(sorted(unknown))}")
    return result


def _topological_order(slices: list[dict[str, Any]]) -> list[str]:
    indegree = {item["id"]: len(item["depends_on"]) for item in slices}
    children = {item["id"]: [] for item in slices}
    for item in slices:
        for dependency in item["depends_on"]:
            children[dependency].append(item["id"])
    ready = deque(sorted(item_id for item_id, degree in indegree.items() if degree == 0))
    ordered = []
    while ready:
        current = ready.popleft()
        ordered.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(ordered) != len(slices):
        raise ValueError("slice dependency graph must be acyclic")
    return ordered


def build_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Build an explicit spec from an approved intake brief and vertical slices."""
    brief = args.get("brief")
    if not isinstance(brief, dict):
        raise ValueError("brief must be an object")
    decision = _approval(args.get("decision"))
    if brief.get("status") != "ready" or decision is None or decision["state"] != "approved":
        return {
            "status": "needs_decision",
            "decisions": [{
                "id": decision["id"] if decision else "brief-approval",
                "owner": decision["owner"] if decision else "PO",
                "state": "needs_input",
                "question": "Record an explicit approved decision for a ready brief before creating a spec.",
            }],
        }
    pm_brief, po_brief = brief.get("pm_brief"), brief.get("po_brief")
    if not isinstance(pm_brief, dict) or not isinstance(po_brief, dict):
        raise ValueError("brief must contain pm_brief and po_brief objects")
    slices = _slices(args.get("slices"))
    return {
        "status": "ready",
        "spec": {
            "problem": _non_empty_string(pm_brief.get("problem"), "brief.pm_brief.problem"),
            "target_user": _non_empty_string(pm_brief.get("target_user"), "brief.pm_brief.target_user"),
            "value_hypothesis": _non_empty_string(po_brief.get("value_hypothesis"), "brief.po_brief.value_hypothesis"),
            "behavior": _non_empty_string(args.get("behavior"), "behavior"),
            "public_test_limits": _non_empty_string(args.get("public_test_limits"), "public_test_limits"),
            "decisions": [decision],
            "skill_lock": _skill_lock(args.get("skill_lock")),
            "stories": slices,
            "execution_order": _topological_order(slices),
        },
    }
