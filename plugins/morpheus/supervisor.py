"""Local durable claims, fencing, and checkpoints for Morpheus slices."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import fcntl

from hermes_constants import get_hermes_home


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA = re.compile(r"^[0-9a-f]{7,64}$")
_OPERATIONS = {"claim", "heartbeat", "checkpoint", "publish", "resume"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _IDENTIFIER.fullmatch(result):
        raise ValueError(f"{field} must contain only letters, numbers, dots, underscores, or hyphens")
    return result


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


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
        / "durable-runs.json"
    )


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "runs": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("durable run state is not valid JSON") from exc
    if not isinstance(state, dict) or not isinstance(state.get("runs"), dict):
        raise ValueError("durable run state has invalid structure")
    return state


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="durable-runs-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            json.dump(state, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


@contextmanager
def _state_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / "durable-runs.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _run_key(repository: str, task_id: str) -> str:
    return f"{repository}:{task_id}"


def _run_args(args: dict[str, Any]) -> tuple[str, str, str, str, int, Path]:
    project_id = _identifier(args.get("project_id"), "project_id")
    repository = _text(args.get("repository"), "repository")
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use owner/name form")
    task_id = _identifier(args.get("task_id"), "task_id")
    worker_id = _identifier(args.get("worker_id"), "worker_id")
    now = _non_negative_int(args.get("now_epoch"), "now_epoch")
    return project_id, repository, task_id, worker_id, now, _state_path(project_id)


def _claim_payload(run: dict[str, Any]) -> dict[str, Any]:
    return {"worker_id": run["worker_id"], "fencing_token": run["fencing_token"], "expires_at": run["expires_at"]}


def _manage_durable_run(args: dict[str, Any]) -> dict[str, Any]:
    """Manage local claims without starting workers or publishing remotely."""
    operation = _text(args.get("operation"), "operation")
    if operation not in _OPERATIONS:
        raise ValueError("operation must be claim, heartbeat, checkpoint, publish, or resume")
    project_id, repository, task_id, worker_id, now, path = _run_args(args)
    state = _load_state(path)
    key = _run_key(repository, task_id)
    run = state["runs"].get(key)

    if operation == "claim":
        lease_seconds = _non_negative_int(args.get("lease_seconds"), "lease_seconds")
        if lease_seconds == 0:
            raise ValueError("lease_seconds must be greater than zero")
        if run and run["expires_at"] > now:
            return {"status": "denied", "reason": "already_claimed", "claim": _claim_payload(run)}
        fencing_token = (run["fencing_token"] if run else 0) + 1
        run = {
            "worker_id": worker_id,
            "fencing_token": fencing_token,
            "expires_at": now + lease_seconds,
            "checkpoint": run.get("checkpoint") if run else None,
        }
        state["runs"][key] = run
        _write_state(path, state)
        return {"status": "claimed", "claim": _claim_payload(run)}

    if run is None:
        return {"status": "denied", "reason": "claim_not_found"}
    fencing_token = _non_negative_int(args.get("fencing_token"), "fencing_token")
    if fencing_token != run["fencing_token"] or worker_id != run["worker_id"]:
        return {"status": "denied", "reason": "fencing_mismatch"}
    if run["expires_at"] <= now:
        return {"status": "denied", "reason": "worker_expired"}

    if operation == "heartbeat":
        lease_seconds = _non_negative_int(args.get("lease_seconds"), "lease_seconds")
        if lease_seconds == 0:
            raise ValueError("lease_seconds must be greater than zero")
        run["expires_at"] = now + lease_seconds
        _write_state(path, state)
        return {"status": "renewed", "claim": _claim_payload(run)}

    if operation == "checkpoint":
        run["checkpoint"] = {
            "spec_sha": _sha(args.get("spec_sha"), "spec_sha"),
            "head_sha": _sha(args.get("head_sha"), "head_sha"),
        }
        _write_state(path, state)
        return {"status": "checkpointed", "checkpoint": run["checkpoint"]}

    if operation == "publish":
        checkpoint = run.get("checkpoint")
        if not checkpoint:
            return {"status": "denied", "reason": "checkpoint_required"}
        if checkpoint != {"spec_sha": _sha(args.get("spec_sha"), "spec_sha"), "head_sha": _sha(args.get("head_sha"), "head_sha")}:
            return {"status": "denied", "reason": "checkpoint_mismatch"}
        return {"status": "permitted", "publish": {"remote_publish_started": False, "checkpoint": checkpoint}}

    checkpoint = run.get("checkpoint")
    expected = {"spec_sha": _sha(args.get("spec_sha"), "spec_sha"), "head_sha": _sha(args.get("head_sha"), "head_sha")}
    if checkpoint is None:
        return {"status": "resume_required", "resume_from": "before_checkpoint", "verified": False}
    if checkpoint != expected:
        return {"status": "denied", "reason": "checkpoint_mismatch"}
    return {"status": "resume_ready", "resume_from": "after_checkpoint", "verified": True, "checkpoint": checkpoint}


def manage_durable_run(args: dict[str, Any]) -> dict[str, Any]:
    """Serialize state transitions so concurrent claims cannot share a writer."""
    project_id = _identifier(args.get("project_id"), "project_id")
    with _state_lock(_state_path(project_id)):
        return _manage_durable_run(args)
