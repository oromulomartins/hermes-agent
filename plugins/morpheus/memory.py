"""Private, project-bound memory and handoff artifacts for Morpheus."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from hermes_constants import get_hermes_home


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_WRITER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_OPERATIONS = {"append", "read"}
_RECORD_KINDS = {"memory", "handoff"}


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
    storage = value.get("storage")
    if not isinstance(storage, dict):
        raise ValueError("binding.storage must be an object")
    return {
        "project_id": project_id,
        "state": _text(storage.get("state"), "binding.storage.state"),
    }


def _project_key(project_id: str) -> str:
    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]


def _store_path(project_id: str) -> Path:
    return (
        get_hermes_home()
        / "plugin-data"
        / "morpheus"
        / "projects"
        / _project_key(project_id)
        / "private-memory.json"
    )


def _artifact_refs(value: Any, kind: str) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("record.artifact_refs must be an array of relative paths")
    refs = []
    for item in value:
        path = PurePosixPath(item.strip())
        if not item.strip() or path.is_absolute() or ".." in path.parts:
            raise ValueError("record.artifact_refs must contain relative paths within the project")
        refs.append(str(path))
    if kind == "handoff" and not refs:
        raise ValueError("handoff records must reference at least one project artifact")
    return refs


def _record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("record must be an object")
    kind = _text(value.get("kind"), "record.kind")
    if kind not in _RECORD_KINDS:
        raise ValueError("record.kind must be memory or handoff")
    return {
        "kind": kind,
        "summary": _text(value.get("summary"), "record.summary"),
        "artifact_refs": _artifact_refs(value.get("artifact_refs"), kind),
    }


def _load_records(path: Path, project_id: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("private memory store is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("project_id") != project_id:
        raise PermissionError("private memory store does not match authenticated project")
    records = payload.get("records")
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise ValueError("private memory store has invalid records")
    return records


def _write_records(path: Path, project_id: str, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "project_id": project_id, "records": records}
    descriptor, temporary_name = tempfile.mkstemp(prefix="private-memory-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def build_private_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Append or retrieve records only within the authenticated project binding."""
    binding = _binding(args.get("binding"))
    authenticated_project = _text(args.get("authenticated_project"), "authenticated_project")
    if binding["project_id"] != authenticated_project:
        raise PermissionError("private memory binding does not match authenticated project")
    operation = _text(args.get("operation"), "operation")
    if operation not in _OPERATIONS:
        raise ValueError("operation must be append or read")

    path = _store_path(binding["project_id"])
    records = _load_records(path, binding["project_id"])
    result: dict[str, Any] = {
        "status": "ready",
        "project_id": binding["project_id"],
        "records": records,
        "coordination": {
            "project_artifact_root": f"{binding['state']}/artifacts",
            "shared_between_projects": False,
        },
    }
    if operation == "read":
        return result

    writer_id = _text(args.get("writer_id"), "writer_id")
    if not _WRITER_ID.fullmatch(writer_id):
        raise ValueError("writer_id must contain only letters, numbers, underscores, or hyphens")
    record = _record(args.get("record"))
    record["id"] = f"{record['kind']}-{len(records) + 1}"
    record["writer_id"] = writer_id
    records.append(record)
    _write_records(path, binding["project_id"], records)
    result["records"] = records
    result["coordination"]["writer_home"] = f"{binding['state']}/writers/{writer_id}/home"
    return result
