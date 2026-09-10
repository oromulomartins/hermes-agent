"""Idempotent, bound-project backlog reconciliation for the Morpheus plugin."""

from __future__ import annotations

from typing import Any


_REQUIRED_ITEM_FIELDS = ("source_id", "issue_type", "summary")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("items must be an array")
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")
        normalized = {field: _text(item.get(field), f"item.{field}") for field in _REQUIRED_ITEM_FIELDS}
        if normalized["source_id"] in seen:
            raise ValueError(f"duplicate source_id in items: {normalized['source_id']}")
        seen.add(normalized["source_id"])
        parent = item.get("parent_source_id")
        if parent is not None:
            normalized["parent_source_id"] = _text(parent, "item.parent_source_id")
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) or not dep.strip() for dep in dependencies):
            raise ValueError("item.depends_on must be an array of non-empty strings")
        normalized["depends_on"] = [dep.strip() for dep in dependencies]
        result.append(normalized)
    known = {item["source_id"] for item in result}
    missing = {
        reference
        for item in result
        for reference in [*item.get("depends_on", []), *([item["parent_source_id"]] if "parent_source_id" in item else [])]
        if reference not in known
    }
    if missing:
        raise ValueError(f"backlog references unknown source ids: {', '.join(sorted(missing))}")
    return result


def _existing(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("existing_items must be an array")
    result = {}
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each existing item must be an object")
        source_id = _text(item.get("source_id"), "existing_item.source_id")
        if source_id in result:
            raise ValueError(f"duplicate source_id in existing_items: {source_id}")
        result[source_id] = {
            "issue_key": _text(item.get("issue_key"), "existing_item.issue_key"),
            "summary": _text(item.get("summary"), "existing_item.summary"),
        }
    return result


def reconcile_backlog(args: dict[str, Any]) -> dict[str, Any]:
    """Return an idempotent Jira publication plan without performing remote writes."""
    bound_project = _text(args.get("bound_project"), "bound_project")
    project = _text(args.get("project"), "project")
    if project != bound_project:
        raise PermissionError(f"project {project!r} is outside the configured binding {bound_project!r}")
    items = _items(args.get("items"))
    existing = _existing(args.get("existing_items", []))
    create, update, unchanged = [], [], []
    for item in items:
        prior = existing.get(item["source_id"])
        if prior is None:
            create.append(item)
        elif prior["summary"] == item["summary"]:
            unchanged.append({"source_id": item["source_id"], "issue_key": prior["issue_key"]})
        else:
            update.append({**item, "issue_key": prior["issue_key"]})
    return {
        "project": project,
        "status": "ready",
        "create": create,
        "update": update,
        "unchanged": unchanged,
        "idempotency_key": f"{project}:{'|'.join(item['source_id'] for item in items)}",
    }
