"""Declarative, quarantine-first onboarding for received repositories."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from typing import Any


_CURATED_KINDS = {"hook", "plugin", "mcp", "script"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _path(value: Any) -> str:
    path = PurePosixPath(_text(value, "file.path"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("file.path must be a relative path within the received repository")
    return str(path)


def _kind(path: PurePosixPath) -> str:
    if path.parts[:2] == (".git", "hooks"):
        return "hook"
    if path.name in {".mcp.json", "mcp.json"} or "mcp" in path.parts:
        return "mcp"
    if path.name == "plugin.yaml" or "plugins" in path.parts:
        return "plugin"
    if path.suffix in {".sh", ".py", ".js", ".ts"} or "scripts" in path.parts:
        return "script"
    return "other"


def _inventory(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("files must be an array")
    result = []
    known_paths = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("files must contain objects")
        path_text = _path(item.get("path"))
        if path_text in known_paths:
            raise ValueError("files must not contain duplicate paths")
        known_paths.add(path_text)
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("file.content must be a string")
        path = PurePosixPath(path_text)
        result.append(
            {
                "path": path_text,
                "kind": _kind(path),
                "digest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    return sorted(result, key=lambda item: item["path"])


def _capabilities(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    return sorted(set(item.strip() for item in value))


def _curated_catalog(
    value: Any, inventory: list[dict[str, str]], approved_capabilities: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise ValueError("curated_extensions must be an array")
    known = {item["path"]: item for item in inventory}
    approved = set(approved_capabilities)
    mounted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for extension in value:
        if not isinstance(extension, dict):
            raise ValueError("curated_extensions must contain objects")
        path = _path(extension.get("path"))
        origin = _text(extension.get("origin"), "curated_extensions.origin")
        digest = _text(extension.get("digest"), "curated_extensions.digest")
        capabilities = _capabilities(extension.get("capabilities"), "curated_extensions.capabilities")
        item = known.get(path)
        if item is None or item["kind"] not in _CURATED_KINDS:
            rejected.append({"path": path, "reason": "not_an_inventory_extension"})
        elif digest != item["digest"]:
            rejected.append({"path": path, "reason": "digest_mismatch"})
        elif not set(capabilities).issubset(approved):
            rejected.append({"path": path, "reason": "capability_not_authorized"})
        else:
            mounted.append(
                {
                    "path": path,
                    "kind": item["kind"],
                    "origin": origin,
                    "digest": digest,
                    "capabilities": capabilities,
                }
            )
    return {"mounted": sorted(mounted, key=lambda item: item["path"]), "rejected": rejected}


def build_repository_onboarding(args: dict[str, Any]) -> dict[str, Any]:
    """Inventory a received repository without executing any discovered content."""
    source_repository = _text(args.get("source_repository"), "source_repository")
    inventory = _inventory(args.get("files"))
    approved_capabilities = _capabilities(args.get("approved_capabilities", []), "approved_capabilities")
    catalog = _curated_catalog(args.get("curated_extensions"), inventory, approved_capabilities)
    return {
        "status": "quarantined",
        "source_repository": source_repository,
        "inventory": inventory,
        "curated_catalog": catalog,
        "execution": {
            "runner_started": False,
            "discovered_extensions_executed": False,
            "reason": "onboarding produces an inventory and mount plan only",
        },
    }
