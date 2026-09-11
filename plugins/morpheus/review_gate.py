"""Fail-closed review gate for a fixed Morpheus delivery SHA."""

from __future__ import annotations

import re
from typing import Any


_SHA = re.compile(r"^[0-9a-f]{7,64}$")
_CHECK_STATES = {"passed", "failed", "skipped", "stale"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _sha(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _SHA.fullmatch(result):
        raise ValueError(f"{field} must be a 7-64 character lowercase hexadecimal SHA")
    return result


def evaluate_review_gate(args: dict[str, Any]) -> dict[str, Any]:
    """Permit a merge only after independent review and current passing checks."""
    _text(args.get("ticket_id"), "ticket_id")
    spec_sha = _sha(args.get("spec_sha"), "spec_sha")
    reviewed_sha = _sha(args.get("reviewed_sha"), "reviewed_sha")
    current_sha = _sha(args.get("current_sha"), "current_sha")
    contexts = args.get("review_contexts")
    if not isinstance(contexts, list) or set(contexts) != {"spec", "standards"} or len(contexts) != 2:
        raise ValueError("review_contexts must contain independent spec and standards reviews")
    if current_sha != reviewed_sha:
        return {"status": "needs_review", "reason": "review_stale", "reviewed_sha": reviewed_sha, "current_sha": current_sha}
    checks = args.get("checks")
    if not isinstance(checks, list) or not checks:
        return {"status": "blocked", "reason": "required_checks_missing"}
    names = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("checks must contain objects")
        name = _text(check.get("name"), "check.name")
        state = _text(check.get("status"), "check.status")
        if state not in _CHECK_STATES:
            raise ValueError("check.status must be passed, failed, skipped, or stale")
        if state != "passed" or _sha(check.get("sha"), "check.sha") != current_sha:
            return {"status": "blocked", "reason": "required_checks_not_current_and_passing"}
        names.append(name)
    authorized = args.get("human_merge_authorized")
    if not isinstance(authorized, bool):
        raise ValueError("human_merge_authorized must be a boolean")
    if not authorized:
        return {"status": "awaiting_human_authorization", "reviewed_sha": reviewed_sha}
    return {"status": "merge_permitted", "reviewed_sha": reviewed_sha, "spec_sha": spec_sha, "checks": names, "human_merge_authorized": True}
