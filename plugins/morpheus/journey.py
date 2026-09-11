"""Synthetic, project-local delivery journey exposed through Morpheus."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_DELIVERY_STATES = {"created", "packed", "in_transit", "delivered"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _IDENTIFIER.fullmatch(result):
        raise ValueError(f"{field} must contain only letters, numbers, dots, underscores, or hyphens")
    return result


def _project_key(project_id: str) -> str:
    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]


def _state_path(project_id: str) -> Path:
    return (
        get_hermes_home()
        / "plugin-data"
        / "morpheus"
        / "projects"
        / _project_key(project_id)
        / "synthetic-delivery-journeys.json"
    )


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "journeys": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("synthetic journey store is not valid JSON") from exc
    if not isinstance(state, dict) or not isinstance(state.get("journeys"), dict):
        raise ValueError("synthetic journey store has invalid structure")
    return state


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="synthetic-journeys-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            json.dump(state, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _journey(project_id: str, journey_id: str, record: dict[str, str]) -> dict[str, Any]:
    order_id = record["order_id"]
    delivery_state = record["delivery_state"]
    return {
        "id": journey_id,
        "ticket_id": record["ticket_id"],
        "api": {
            "method": "GET",
            "path": f"/api/morpheus/projects/{project_id}/delivery-journeys/{journey_id}",
            "response": {"order_id": order_id, "delivery_state": delivery_state},
        },
        "web": {
            "path": f"/morpheus/projects/{project_id}/delivery-journeys/{journey_id}",
            "title": "Delivery status",
            "delivery_state": delivery_state,
        },
    }


def _result(status: str, project_id: str, journey_id: str, record: dict[str, str]) -> dict[str, Any]:
    return {
        "status": status,
        "journey": _journey(project_id, journey_id, record),
        "persistence": {"kind": "local-json", "project_scoped": True, "network": "none"},
    }


def run_synthetic_delivery_journey(args: dict[str, Any]) -> dict[str, Any]:
    """Create or read one synthetic delivery journey without network access."""
    operation = _text(args.get("operation"), "operation")
    if operation not in {"create", "read"}:
        raise ValueError("operation must be create or read")
    project_id = _identifier(args.get("project_id"), "project_id")
    journey_id = _identifier(args.get("journey_id"), "journey_id")
    path = _state_path(project_id)
    state = _load_state(path)
    existing = state["journeys"].get(journey_id)

    if operation == "read":
        if existing is None:
            return {"status": "not_found", "journey_id": journey_id}
        return _result("ready", project_id, journey_id, existing)

    ticket_id = _identifier(args.get("ticket_id"), "ticket_id")
    order_id = _identifier(args.get("order_id"), "order_id")
    if not order_id.startswith("synthetic-"):
        raise ValueError("order_id must use a synthetic order identifier")
    delivery_state = _text(args.get("delivery_state"), "delivery_state")
    if delivery_state not in _DELIVERY_STATES:
        raise ValueError("delivery_state must be created, packed, in_transit, or delivered")
    record = {"ticket_id": ticket_id, "order_id": order_id, "delivery_state": delivery_state}

    if existing is not None:
        if existing != record:
            raise ValueError("journey_id already exists with different synthetic data")
        return _result("existing", project_id, journey_id, existing)

    state["journeys"][journey_id] = record
    _write_state(path, state)
    return _result("created", project_id, journey_id, record)
