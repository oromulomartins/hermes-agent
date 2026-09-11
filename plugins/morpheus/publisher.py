"""Idempotent local receipts for verified remote publication evidence."""

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
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH = re.compile(r"^work/[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_SHA = re.compile(r"^[0-9a-f]{7,64}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _IDENTIFIER.fullmatch(result):
        raise ValueError(f"{field} must contain only letters, numbers, dots, underscores, or hyphens")
    return result


def _sha(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _SHA.fullmatch(result):
        raise ValueError(f"{field} must be a 7-64 character lowercase hexadecimal SHA")
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
        / "publication-receipts.json"
    )


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "receipts": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("publication receipt store is not valid JSON") from exc
    if not isinstance(state, dict) or not isinstance(state.get("receipts"), dict):
        raise ValueError("publication receipt store has invalid structure")
    return state


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="publication-receipts-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            json.dump(state, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _receipt(args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    project_id = _identifier(args.get("project_id"), "project_id")
    repository = _text(args.get("repository"), "repository")
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use owner/name form")
    ticket_id = _identifier(args.get("ticket_id"), "ticket_id")
    branch = _text(args.get("branch"), "branch")
    if not _BRANCH.fullmatch(branch):
        raise ValueError("branch must be a work/ branch with a safe name")
    base_sha = _sha(args.get("base_sha"), "base_sha")
    expected_head_sha = _sha(args.get("expected_head_sha"), "expected_head_sha")
    remote_head_sha = _sha(args.get("remote_head_sha"), "remote_head_sha")
    if remote_head_sha != expected_head_sha:
        raise ValueError("remote_head_sha does not match expected_head_sha")
    pr_number = args.get("pr_number")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0:
        raise ValueError("pr_number must be a positive integer")
    receipt = {
        "repository": repository,
        "ticket_id": ticket_id,
        "branch": branch,
        "base_sha": base_sha,
        "head_sha": expected_head_sha,
        "pr_number": pr_number,
        "evidence": {
            "problem": _text(args.get("problem"), "problem"),
            "behavior": _text(args.get("behavior"), "behavior"),
            "spec_sha": _sha(args.get("spec_sha"), "spec_sha"),
            "test_evidence": _text(args.get("test_evidence"), "test_evidence"),
        },
        "remote_write_started": False,
    }
    return project_id, receipt


def reconcile_publication(args: dict[str, Any]) -> dict[str, Any]:
    """Record one verified publication receipt without starting remote writes."""
    project_id, receipt = _receipt(args)
    path = _state_path(project_id)
    state = _load_state(path)
    key = f"{receipt['repository']}:{receipt['ticket_id']}"
    existing = state["receipts"].get(key)
    if existing is not None:
        if existing != receipt:
            raise ValueError("publication receipt already exists with different evidence")
        return {"status": "reconciled", "receipt": existing}
    state["receipts"][key] = receipt
    _write_state(path, state)
    return {"status": "recorded", "receipt": receipt}
