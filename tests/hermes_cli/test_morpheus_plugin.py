"""Behavioral coverage for the opt-in Morpheus plugin."""

from __future__ import annotations

import hashlib
import json

import pytest

from hermes_cli.plugins import PluginManager
from plugins.morpheus.backlog import reconcile_backlog
from plugins.morpheus.binding import build_project_binding
from plugins.morpheus.broker import build_scoped_tool_grant
from plugins.morpheus.memory import build_private_memory
from plugins.morpheus.onboarding import build_repository_onboarding
from plugins.morpheus.isolation import run_tenant_isolation_proof
from plugins.morpheus.spec import build_spec
from plugins.morpheus.specialists import route_curated_specialist
from plugins.morpheus.supervisor import manage_durable_run
from plugins.morpheus.worker import build_isolated_worker
from tools.registry import registry


def _enable_morpheus_plugin(home):
    home.mkdir()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled:\n"
        "    - morpheus\n",
        encoding="utf-8",
    )


def _enabled_manager(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    _enable_morpheus_plugin(home)
    monkeypatch.setenv("HERMES_HOME", str(home))
    manager = PluginManager()
    manager.discover_and_load()
    return manager


def _ready_brief():
    return {
        "status": "ready",
        "pm_brief": {
            "target_user": "Online shoppers",
            "problem": "Buyers lack timely delivery visibility.",
        },
        "po_brief": {
            "value_hypothesis": "Fewer support requests about delivery status.",
        },
    }


def _spec_args():
    return {
        "brief": _ready_brief(),
        "decision": {"id": "DEC-1", "owner": "PO", "state": "approved"},
        "behavior": "Show a delivery lifecycle state for a selected order.",
        "public_test_limits": "Use synthetic order and shipment identifiers only.",
        "skill_lock": {
            "name": "matt-jira",
            "revision": "2026-09-10",
            "adaptations": ["Jira cards are the delivery tracker."],
        },
        "slices": [
            {
                "id": "delivery-read",
                "title": "Read delivery state",
                "value": "Buyer sees shipment progress",
                "acceptance": "Synthetic order returns its lifecycle state",
                "blockers": "None",
                "depends_on": [],
            },
            {
                "id": "delivery-view",
                "title": "Display delivery state",
                "value": "Buyer can understand shipment progress",
                "acceptance": "Lifecycle state is visible in the order view",
                "blockers": "delivery-read",
                "depends_on": ["delivery-read"],
            },
        ],
    }


def test_morpheus_plugin_registers_namespaced_diagnostic_when_enabled(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    assert manager._plugins["morpheus"].enabled is True
    assert "morpheus-status" in manager._plugin_commands

    raw = registry.dispatch("morpheus_status", {}, scope=manager.scope_key)
    payload = json.loads(raw)

    assert payload["plugin"] == "morpheus"
    assert payload["capabilities"]["spec_slices"] is True
    assert payload["capabilities"]["backlog_reconcile"] is True
    assert payload["capabilities"]["project_binding"] is True
    assert payload["capabilities"]["isolated_worker_plan"] is True
    assert payload["capabilities"]["private_project_memory"] is True
    assert payload["capabilities"]["scoped_tool_grant"] is True
    assert payload["capabilities"]["repository_onboarding"] is True
    assert payload["capabilities"]["tenant_isolation_proof"] is True
    assert payload["capabilities"]["durable_run_supervisor"] is True
    assert payload["capabilities"]["curated_web_specialists"] is True


def test_morpheus_intake_produces_separate_briefs_and_persists_glossary(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch(
        "morpheus_intake_brief",
        {
            "project": "Synthetic Commerce",
            "demand": "Help buyers track the status of a delivery.",
            "target_user": "Online shoppers",
            "problem": "Buyers lack timely delivery visibility.",
            "value_hypothesis": "Fewer support requests about delivery status.",
            "constraints": ["Use synthetic data only."],
            "terms": {"delivery status": "Current lifecycle state of an order shipment."},
        },
        scope=manager.scope_key,
    )
    brief = json.loads(raw)

    assert brief["status"] == "ready"
    assert brief["pm_brief"]["target_user"] == "Online shoppers"
    assert brief["po_brief"]["value_hypothesis"] == "Fewer support requests about delivery status."
    assert brief["questions"] == []
    assert brief["glossary"]["delivery status"] == "Current lifecycle state of an order shipment."


def test_morpheus_intake_marks_missing_information_as_needs_input(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch(
        "morpheus_intake_brief",
        {"project": "Synthetic Commerce", "demand": "Improve the buying experience."},
        scope=manager.scope_key,
    )
    brief = json.loads(raw)

    assert brief["status"] == "needs_input"
    assert {question["field"] for question in brief["questions"]} == {
        "target_user",
        "problem",
        "value_hypothesis",
    }


def test_morpheus_spec_requires_explicit_approval():
    result = build_spec({**_spec_args(), "decision": {"id": "DEC-1", "owner": "PO", "state": "pending"}})

    assert result["status"] == "needs_decision"
    assert result["decisions"][0]["state"] == "needs_input"


def test_morpheus_spec_builds_an_acyclic_vertical_slice_dag(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch("morpheus_spec_slices", _spec_args(), scope=manager.scope_key)
    result = json.loads(raw)

    assert result["status"] == "ready"
    assert result["spec"]["execution_order"] == ["delivery-read", "delivery-view"]
    assert result["spec"]["decisions"] == [{"id": "DEC-1", "owner": "PO", "state": "approved"}]
    assert result["spec"]["skill_lock"]["name"] == "matt-jira"


def test_morpheus_spec_rejects_a_cyclic_slice_graph():
    args = _spec_args()
    args["slices"][0]["depends_on"] = ["delivery-view"]

    with pytest.raises(ValueError, match="acyclic"):
        build_spec(args)


def test_morpheus_plugin_does_not_register_when_not_enabled(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))

    manager = PluginManager()
    manager.discover_and_load()

    assert "morpheus" not in {name for name, plugin in manager._plugins.items() if plugin.enabled}
    assert "morpheus_status" not in manager._plugin_tool_names
    assert "morpheus_intake_brief" not in manager._plugin_tool_names
    assert "morpheus_spec_slices" not in manager._plugin_tool_names


def _backlog_items():
    return [
        {
            "source_id": "MP-001",
            "issue_type": "Task",
            "summary": "Bootstrap Morpheus",
            "depends_on": [],
        },
        {
            "source_id": "MP-002",
            "issue_type": "Story",
            "summary": "Enable Morpheus",
            "parent_source_id": "MP-001",
            "depends_on": ["MP-001"],
        },
    ]


def test_morpheus_backlog_reconciliation_is_idempotent(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    args = {
        "bound_project": "BPT",
        "project": "BPT",
        "items": _backlog_items(),
        "existing_items": [{"source_id": "MP-001", "issue_key": "BPT-9", "summary": "Bootstrap Morpheus"}],
    }

    first = json.loads(registry.dispatch("morpheus_backlog_reconcile", args, scope=manager.scope_key))
    repeated = reconcile_backlog({**args, "existing_items": [
        {"source_id": "MP-001", "issue_key": "BPT-9", "summary": "Bootstrap Morpheus"},
        {"source_id": "MP-002", "issue_key": "BPT-10", "summary": "Enable Morpheus"},
    ]})

    assert [item["source_id"] for item in first["create"]] == ["MP-002"]
    assert first["unchanged"] == [{"source_id": "MP-001", "issue_key": "BPT-9"}]
    assert repeated["create"] == []
    assert {item["issue_key"] for item in repeated["unchanged"]} == {"BPT-9", "BPT-10"}


def test_morpheus_backlog_reconciliation_rejects_project_outside_binding():
    with pytest.raises(PermissionError, match="outside the configured binding"):
        reconcile_backlog({
            "bound_project": "BPT",
            "project": "OTHER",
            "items": _backlog_items(),
        })


def test_morpheus_backlog_reconciliation_rejects_duplicate_source_ids():
    with pytest.raises(ValueError, match="duplicate source_id"):
        reconcile_backlog({
            "bound_project": "BPT",
            "project": "BPT",
            "items": [_backlog_items()[0], _backlog_items()[0]],
        })


def _binding_args():
    return {
        "authenticated_project": "synthetic-customer-a",
        "requested_project": "synthetic-customer-a",
        "repository": "oromulomartins/hermes-agent",
        "jira_project": "BPT",
        "secret_refs": {"github": "secret://synthetic-customer-a/github"},
    }


def test_morpheus_project_binding_uses_local_docker_and_private_paths(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch("morpheus_project_binding", _binding_args(), scope=manager.scope_key)
    result = json.loads(raw)

    binding = result["binding"]
    assert binding["runtime"] == {
        "kind": "docker-local",
        "container_name": binding["runtime"]["container_name"],
        "network": "none",
        "read_only_root_filesystem": True,
    }
    assert binding["runtime"]["container_name"].startswith("morpheus-synthetic-customer-a-")
    assert "synthetic-customer-a" in binding["storage"]["workspace"]
    assert binding["secret_refs"] == {"github": "secret://synthetic-customer-a/github"}
    assert result["policy"]["external_provisioning"] is False

    other_args = _binding_args()
    other_args["authenticated_project"] = "synthetic-customer-b"
    other_args["requested_project"] = "synthetic-customer-b"
    other = build_project_binding(other_args)["binding"]

    assert other["runtime"]["container_name"] != binding["runtime"]["container_name"]
    assert other["storage"] != binding["storage"]


def test_morpheus_project_binding_rejects_a_conflicting_requested_project():
    args = _binding_args()
    args["requested_project"] = "synthetic-customer-b"

    with pytest.raises(PermissionError, match="does not match"):
        build_project_binding(args)


def test_morpheus_project_binding_rejects_credential_values():
    args = _binding_args()
    args["secret_refs"] = {"github": "ghp-not-a-reference"}

    with pytest.raises(ValueError, match="secret:// reference"):
        build_project_binding(args)


def _worker_args():
    binding = build_project_binding(_binding_args())["binding"]
    return {
        "authenticated_project": "synthetic-customer-a",
        "binding": binding,
        "run_id": "run-001",
    }


def test_morpheus_isolated_worker_plan_has_no_network_host_socket_or_credentials(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    raw = registry.dispatch("morpheus_isolated_worker", _worker_args(), scope=manager.scope_key)
    result = json.loads(raw)

    worker = result["worker"]
    assert worker["network"] == "none"
    assert worker["user"] == "65532:65532"
    assert worker["privileged"] is False
    assert worker["docker_socket"] is False
    assert worker["drop_capabilities"] == ["ALL"]
    assert {mount["target"] for mount in worker["mounts"]} == {"/workspace", "/home/worker"}
    assert "secret" not in json.dumps(worker)
    assert result["cleanup"]["retain_authenticated_cache"] is False


def test_morpheus_isolated_worker_rejects_a_binding_from_another_project():
    args = _worker_args()
    args["authenticated_project"] = "synthetic-customer-b"

    with pytest.raises(PermissionError, match="does not match"):
        build_isolated_worker(args)


def _private_memory_args():
    return {
        "authenticated_project": "synthetic-customer-a",
        "binding": build_project_binding(_binding_args())["binding"],
    }


def test_morpheus_private_memory_persists_memory_and_project_artifact_handoffs(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    args = _private_memory_args()

    memory = json.loads(registry.dispatch(
        "morpheus_project_memory",
        {
            **args,
            "operation": "append",
            "writer_id": "writer-001",
            "record": {
                "kind": "memory",
                "summary": "Synthetic order identifiers require redaction before a handoff.",
                "artifact_refs": ["notes/redaction.md"],
            },
        },
        scope=manager.scope_key,
    ))
    handoff = json.loads(registry.dispatch(
        "morpheus_project_memory",
        {
            **args,
            "operation": "append",
            "writer_id": "writer-002",
            "record": {
                "kind": "handoff",
                "summary": "Continue with the synthetic redaction test case.",
                "artifact_refs": ["handoffs/run-001.json"],
            },
        },
        scope=manager.scope_key,
    ))
    recovered = build_private_memory({**args, "operation": "read"})

    assert [record["kind"] for record in recovered["records"]] == ["memory", "handoff"]
    assert "writer-001" in memory["coordination"]["writer_home"]
    assert handoff["records"][-1]["artifact_refs"] == ["handoffs/run-001.json"]
    assert recovered["coordination"]["shared_between_projects"] is False


def test_morpheus_private_memory_never_returns_another_projects_records(tmp_path, monkeypatch):
    _enabled_manager(tmp_path, monkeypatch)
    first = _private_memory_args()
    build_private_memory({
        **first,
        "operation": "append",
        "writer_id": "writer-001",
        "record": {
            "kind": "memory",
            "summary": "Synthetic customer A only.",
            "artifact_refs": ["notes/a.md"],
        },
    })
    other_binding_args = _binding_args()
    other_binding_args["authenticated_project"] = "synthetic-customer-b"
    other_binding_args["requested_project"] = "synthetic-customer-b"
    second = {
        "authenticated_project": "synthetic-customer-b",
        "binding": build_project_binding(other_binding_args)["binding"],
        "operation": "read",
    }

    recovered = build_private_memory(second)

    assert recovered["records"] == []
    assert recovered["project_id"] == "synthetic-customer-b"


def test_morpheus_private_memory_rejects_a_binding_from_another_project():
    args = _private_memory_args()
    args["authenticated_project"] = "synthetic-customer-b"
    args["operation"] = "read"

    with pytest.raises(PermissionError, match="does not match"):
        build_private_memory(args)


def _broker_args():
    return {
        "authenticated_project": "synthetic-customer-a",
        "binding": build_project_binding(_binding_args())["binding"],
        "tool": "github",
        "action": "write",
        "requested_scope": "oromulomartins/hermes-agent",
        "now_epoch": 100,
        "expires_at": 400,
    }


def test_morpheus_scoped_tool_grant_limits_github_to_the_bound_repository(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)

    result = json.loads(registry.dispatch(
        "morpheus_scoped_tool_grant", _broker_args(), scope=manager.scope_key
    ))

    assert result["status"] == "granted"
    assert result["grant"]["scope"] == {"repository": "oromulomartins/hermes-agent"}
    assert result["grant"]["credential_material"] == "not_exposed"
    assert result["worker"]["credentials_available"] is False


def test_morpheus_scoped_tool_grant_denies_foreign_scopes_without_recording_them(tmp_path, monkeypatch):
    _enabled_manager(tmp_path, monkeypatch)
    args = _broker_args()
    args["requested_scope"] = "other-customer/private-repository"

    denied = build_scoped_tool_grant(args)
    audit = next((tmp_path / "hermes-home" / "plugin-data" / "morpheus" / "projects").rglob("*.jsonl"))

    assert denied == {
        "status": "denied",
        "reason": "scope_not_authorized",
        "audit": {"event": "tool_access_denied", "recorded": True},
        "worker": {"credentials_available": False},
    }
    assert "other-customer/private-repository" not in audit.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"policy_state": "unavailable"}, "policy_unavailable"),
        ({"expires_at": 100}, "grant_expired"),
    ],
)
def test_morpheus_scoped_tool_grant_denies_policy_failures_and_expired_grants(
    tmp_path, monkeypatch, changes, reason
):
    _enabled_manager(tmp_path, monkeypatch)
    result = build_scoped_tool_grant({**_broker_args(), **changes})

    assert result["status"] == "denied"
    assert result["reason"] == reason
    assert result["audit"]["recorded"] is True


def test_morpheus_repository_onboarding_inventories_untrusted_extensions_without_execution(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    malicious_hook = "touch should-never-run"
    raw = registry.dispatch(
        "morpheus_repository_onboarding",
        {
            "source_repository": "external/synthetic-repository",
            "files": [
                {"path": ".git/hooks/pre-commit", "content": malicious_hook},
                {"path": ".mcp.json", "content": "{\\\"mcpServers\\\": {}}"},
                {"path": "scripts/bootstrap.sh", "content": "echo bootstrap"},
            ],
            "approved_capabilities": [],
        },
        scope=manager.scope_key,
    )
    result = json.loads(raw)

    assert [item["kind"] for item in result["inventory"]] == ["hook", "mcp", "script"]
    assert result["execution"]["runner_started"] is False
    assert result["execution"]["discovered_extensions_executed"] is False
    assert malicious_hook not in json.dumps(result)


def test_morpheus_repository_onboarding_mounts_only_digest_matched_authorized_capabilities():
    plugin_content = "name: curated-plugin\n"
    result = build_repository_onboarding(
        {
            "source_repository": "external/synthetic-repository",
            "files": [{"path": "plugins/curated/plugin.yaml", "content": plugin_content}],
            "approved_capabilities": ["read_files"],
            "curated_extensions": [
                {
                    "path": "plugins/curated/plugin.yaml",
                    "origin": "internal-curated-catalog",
                    "digest": hashlib.sha256(plugin_content.encode("utf-8")).hexdigest(),
                    "capabilities": ["read_files"],
                },
                {
                    "path": "plugins/curated/plugin.yaml",
                    "origin": "untrusted-copy",
                    "digest": "0" * 64,
                    "capabilities": ["write_files"],
                },
            ],
        }
    )

    assert result["curated_catalog"]["mounted"] == [
        {
            "path": "plugins/curated/plugin.yaml",
            "kind": "plugin",
            "origin": "internal-curated-catalog",
            "digest": hashlib.sha256(plugin_content.encode("utf-8")).hexdigest(),
            "capabilities": ["read_files"],
        }
    ]
    assert result["curated_catalog"]["rejected"] == [
        {"path": "plugins/curated/plugin.yaml", "reason": "digest_mismatch"}
    ]


def _isolation_proof_args():
    return {
        "project_id": "synthetic-customer-a",
        "peer_project": "synthetic-customer-b",
        "private_canary": "private-canary-a-must-not-leak",
        "attack_vectors": ["file", "symlink", "memory", "jira", "repository", "network", "artifact"],
        "active_grant_ids": ["grant-001", "grant-002"],
    }


def test_morpheus_tenant_isolation_proof_denies_every_cross_project_vector_privately(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    args = _isolation_proof_args()
    raw = registry.dispatch("morpheus_tenant_isolation_proof", args, scope=manager.scope_key)
    result = json.loads(raw)
    evidence = next((tmp_path / "hermes-home" / "plugin-data" / "morpheus" / "projects").rglob("*.jsonl"))

    assert result["status"] == "contained"
    assert {item["vector"] for item in result["attack_results"]} == set(args["attack_vectors"])
    assert {item["decision"] for item in result["attack_results"]} == {"denied"}
    assert result["control_plane"] == {"received_private_content": False, "central_log_entries": []}
    assert result["evidence"] == {"private_to_project": True, "preserved": True}
    assert args["private_canary"] not in raw
    assert args["peer_project"] not in raw
    assert args["private_canary"] not in evidence.read_text(encoding="utf-8")


def test_morpheus_tenant_isolation_proof_revokes_grants_and_blocks_new_claims(tmp_path, monkeypatch):
    _enabled_manager(tmp_path, monkeypatch)

    result = run_tenant_isolation_proof(_isolation_proof_args())

    assert result["kill_switch"] == {"new_claims": "denied", "revoked_grant_count": 2}


def _durable_run_args():
    return {
        "project_id": "synthetic-customer-a",
        "repository": "oromulomartins/hermes-agent",
        "task_id": "synthetic-task-001",
        "worker_id": "worker-a",
        "now_epoch": 100,
    }


def test_morpheus_durable_run_allows_only_one_active_writer_and_fences_expired_workers(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    args = _durable_run_args()
    claimed = json.loads(registry.dispatch(
        "morpheus_durable_run", {**args, "operation": "claim", "lease_seconds": 10}, scope=manager.scope_key
    ))
    concurrent = manage_durable_run({
        **args,
        "operation": "claim",
        "worker_id": "worker-b",
        "now_epoch": 101,
        "lease_seconds": 10,
    })
    expired_publish = manage_durable_run({
        **args,
        "operation": "publish",
        "now_epoch": 110,
        "fencing_token": claimed["claim"]["fencing_token"],
        "spec_sha": "a" * 40,
        "head_sha": "b" * 40,
    })
    replacement = manage_durable_run({
        **args,
        "operation": "claim",
        "worker_id": "worker-b",
        "now_epoch": 110,
        "lease_seconds": 10,
    })

    assert claimed["status"] == "claimed"
    assert concurrent["reason"] == "already_claimed"
    assert expired_publish == {"status": "denied", "reason": "worker_expired"}
    assert replacement["claim"]["fencing_token"] == claimed["claim"]["fencing_token"] + 1


def test_morpheus_durable_run_resumes_after_matching_checkpoint_and_detects_mismatch(tmp_path, monkeypatch):
    _enabled_manager(tmp_path, monkeypatch)
    args = _durable_run_args()
    claim = manage_durable_run({**args, "operation": "claim", "lease_seconds": 20})["claim"]
    before = manage_durable_run({
        **args,
        "operation": "resume",
        "fencing_token": claim["fencing_token"],
        "spec_sha": "a" * 40,
        "head_sha": "b" * 40,
    })
    checkpoint = manage_durable_run({
        **args,
        "operation": "checkpoint",
        "fencing_token": claim["fencing_token"],
        "spec_sha": "a" * 40,
        "head_sha": "b" * 40,
    })
    after = manage_durable_run({
        **args,
        "operation": "resume",
        "fencing_token": claim["fencing_token"],
        "spec_sha": "a" * 40,
        "head_sha": "b" * 40,
    })
    mismatch = manage_durable_run({
        **args,
        "operation": "resume",
        "fencing_token": claim["fencing_token"],
        "spec_sha": "c" * 40,
        "head_sha": "b" * 40,
    })

    assert before == {"status": "resume_required", "resume_from": "before_checkpoint", "verified": False}
    assert checkpoint["status"] == "checkpointed"
    assert after["status"] == "resume_ready"
    assert after["verified"] is True
    assert mismatch == {"status": "denied", "reason": "checkpoint_mismatch"}


def _specialist_candidates():
    return [
        {
            "name": "awesome-backend",
            "role": "Backend",
            "adapter": "curated-tool-adapter",
            "license": "MIT",
            "sha": "a" * 64,
            "digest": "b" * 64,
        },
        {
            "name": "awesome-frontend",
            "role": "Frontend",
            "adapter": "curated-tool-adapter",
            "license": "Apache-2.0",
            "sha": "c" * 64,
            "digest": "d" * 64,
        },
        {
            "name": "awesome-fullstack",
            "role": "FullStack",
            "adapter": "curated-tool-adapter",
            "license": "MIT",
            "sha": "e" * 64,
            "digest": "f" * 64,
        },
    ]


@pytest.mark.parametrize(
    ("role", "fixture"),
    [("Backend", "fastapi"), ("Frontend", "react"), ("FullStack", "web-api")],
)
def test_morpheus_curated_specialist_routes_each_web_role_to_a_valid_fixture(role, fixture):
    result = route_curated_specialist(
        {
            "project_id": "synthetic-customer-a",
            "requested_role": role,
            "coordinator_role": "TL",
            "fixture": fixture,
            "candidates": _specialist_candidates(),
        }
    )

    assert result["status"] == "ready"
    assert result["specialist"]["role"] == role
    assert result["specialist"]["adapter"] == "curated-tool-adapter"
    assert result["validation"] == {
        "fixture": fixture,
        "output": {"role": role, "adapter": "curated-tool-adapter"},
        "valid": True,
        "executed": False,
    }


def test_morpheus_curated_specialist_limits_coordination_to_the_current_project(tmp_path, monkeypatch):
    manager = _enabled_manager(tmp_path, monkeypatch)
    raw = registry.dispatch(
        "morpheus_curated_specialist",
        {
            "project_id": "synthetic-customer-a",
            "requested_role": "Backend",
            "coordinator_role": "PM",
            "fixture": "fastapi",
            "candidates": _specialist_candidates(),
        },
        scope=manager.scope_key,
    )
    result = json.loads(raw)

    assert result["coordination"] == {
        "role": "PM",
        "scope": "project_only",
        "global_client_context_available": False,
        "may_execute_specialist": False,
    }
    assert result["validation"]["executed"] is False


def test_morpheus_curated_specialist_rejects_candidates_without_a_license():
    candidates = _specialist_candidates()
    candidates[0].pop("license")

    with pytest.raises(ValueError, match="candidate.license"):
        route_curated_specialist(
            {
                "project_id": "synthetic-customer-a",
                "requested_role": "Backend",
                "coordinator_role": "TL",
                "fixture": "fastapi",
                "candidates": candidates,
            }
        )
