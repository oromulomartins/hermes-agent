"""Deterministic intake brief generation for the Morpheus plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


_REQUIRED_FIELDS = {
    "target_user": ("PM", "Who is the target user for this demand?"),
    "problem": ("PM", "What problem does the target user need solved?"),
    "value_hypothesis": ("PO", "What measurable value should this change create?"),
}


def _required_text(args: dict[str, Any], field: str) -> str:
    value = args.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text(args: dict[str, Any], field: str) -> str | None:
    value = args.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    return value or None


def _constraints(args: dict[str, Any]) -> list[str]:
    value = args.get("constraints", [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("constraints must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def _terms(args: dict[str, Any]) -> dict[str, str]:
    value = args.get("terms", {})
    if not isinstance(value, dict):
        raise ValueError("terms must be an object of term-to-definition strings")
    result = {}
    for term, definition in value.items():
        if not isinstance(term, str) or not isinstance(definition, str):
            raise ValueError("terms must be an object of term-to-definition strings")
        clean_term, clean_definition = term.strip(), definition.strip()
        if clean_term and clean_definition:
            result[clean_term] = clean_definition
    return result


def _glossary_path(project: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", project.lower()).strip("-")
    if not slug:
        raise ValueError("project must contain at least one letter or number")
    return get_hermes_home() / "plugin-data" / "morpheus" / "glossaries" / f"{slug}.json"


def _persist_glossary(project: str, terms: dict[str, str]) -> dict[str, str]:
    path = _glossary_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    glossary = {
        str(term): str(definition)
        for term, definition in existing.items()
        if isinstance(term, str) and isinstance(definition, str)
    }
    glossary.update(terms)
    path.write_text(json.dumps(glossary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return glossary


def build_intake_brief(args: dict[str, Any]) -> dict[str, Any]:
    """Create PM and PO artifacts without inventing fields absent from the input."""
    demand = _required_text(args, "demand")
    project = _required_text(args, "project")
    values = {field: _optional_text(args, field) for field in _REQUIRED_FIELDS}
    questions = [
        {
            "field": field,
            "question": question,
            "owner": owner,
            "state": "needs_input",
        }
        for field, (owner, question) in _REQUIRED_FIELDS.items()
        if values[field] is None
    ]
    constraints = _constraints(args)
    glossary = _persist_glossary(project, _terms(args))

    return {
        "project": project,
        "status": "needs_input" if questions else "ready",
        "pm_brief": {
            "demand": demand,
            "target_user": values["target_user"],
            "problem": values["problem"],
            "open_questions": [question for question in questions if question["owner"] == "PM"],
        },
        "po_brief": {
            "value_hypothesis": values["value_hypothesis"],
            "constraints": constraints,
            "open_questions": [question for question in questions if question["owner"] == "PO"],
        },
        "questions": questions,
        "glossary": glossary,
    }
