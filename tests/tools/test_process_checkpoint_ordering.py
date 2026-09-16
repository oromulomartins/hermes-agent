"""Checkpoint publication ordering, adapted from Liuzikaii's upstream PR #109985."""

import errno
import json
import logging
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from hermes_cli._subprocess_compat import windows_hide_flags
from tools.process_registry import ProcessRegistry, ProcessSession


@pytest.mark.asyncio
async def test_concurrent_checkpoints_recover_all_live_processes(tmp_path, monkeypatch):
    import gateway.run as gateway_run
    from gateway.run_startup import GatewayStartupMixin
    import tools.process_registry as pr
    import utils

    checkpoint = tmp_path / "processes.json"
    monkeypatch.setattr(pr, "CHECKPOINT_PATH", checkpoint)
    registry = ProcessRegistry()
    old_entered, release_old, contender_probed = (threading.Event() for _ in range(3))
    real_write = utils.atomic_json_write
    publications = []
    processes = []
    contention = []

    def ordered_write(path, entries, **kwargs):
        ids = [item["session_id"] for item in entries]
        if ids == ["first"]:
            old_entered.set()
            if not release_old.wait(10):
                raise TimeoutError("old writer was not released")
        real_write(path, entries, **kwargs)
        publications.append(ids)

    def add_session(index, name):
        if index:
            # Probe the real lock, not elapsed time, to choose the adversarial
            # schedule: publish the newer snapshot first if serialization is absent.
            acquired = registry._lock.acquire(blocking=False)
            if acquired:
                registry._lock.release()
            contention.append(not acquired)
            contender_probed.set()
        with registry._lock:
            registry._running[name] = ProcessSession(
                id=name, command="checkpoint sleeping child", task_id="checkpoint",
                pid=processes[index].pid,
                host_start_time=registry._safe_host_start_time(processes[index].pid),
            )
        registry._write_checkpoint()

    monkeypatch.setattr(utils, "atomic_json_write", ordered_write)
    try:
        for _ in range(2):
            processes.append(subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                creationflags=windows_hide_flags(),
            ))
        with ThreadPoolExecutor(max_workers=2) as pool:
            old = pool.submit(add_session, 0, "first")
            try:
                assert old_entered.wait(10)
                newer = pool.submit(add_session, 1, "second")
                assert contender_probed.wait(10)
                if not contention[0]:
                    newer.result(timeout=10)
            finally:
                release_old.set()
            old.result(timeout=10)
            newer.result(timeout=10)
        restored = ProcessRegistry()
        monkeypatch.setattr(pr, "process_registry", restored)
        monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
        # Exercise the actual gateway restart recovery phase, isolating unrelated
        # plugins/platforms/session recovery so no external services are contacted.
        runner = SimpleNamespace(
            _start_register_plugins_relay_hooks=Mock(), hooks=Mock(),
            _recover_unclean_sessions=AsyncMock(return_value=(0, 0)),
            _suspend_stuck_loop_sessions=Mock(return_value=0),
        )
        await GatewayStartupMixin._start_recover_previous_run(runner)
        assert set(restored._running) == {"first", "second"}
        assert publications[:2] == [["first"], ["first", "second"]]
        assert all(session.detached for session in restored._running.values())
    finally:
        release_old.set()
        for process in processes:
            process.terminate()
            process.wait(timeout=10)


def test_checkpoint_replace_failure_preserves_last_snapshot(tmp_path, monkeypatch, caplog):
    import tools.process_registry as pr
    import utils

    checkpoint = tmp_path / "processes.json"
    monkeypatch.setattr(pr, "CHECKPOINT_PATH", checkpoint)
    registry = ProcessRegistry()
    registry._running["first"] = ProcessSession(id="first", command="sleep 60")
    registry._write_checkpoint()
    original = checkpoint.read_bytes()

    def fail_replace(source, destination):
        raise OSError(errno.EIO, "injected checkpoint replace failure")

    with monkeypatch.context() as patch:
        patch.setattr(utils, "atomic_replace", fail_replace)
        with caplog.at_level(logging.DEBUG, logger="tools.process_registry"):
            registry._running["second"] = ProcessSession(id="second", command="sleep 60")
            registry._write_checkpoint()
    assert checkpoint.read_bytes() == original
    assert not list(tmp_path.glob(".processes_*"))
    assert "Failed to write checkpoint file" in caplog.text
    # A subsequent writer must still acquire the lock after the failed replace.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(registry._write_checkpoint).result(timeout=10)
    assert {entry["session_id"] for entry in json.loads(checkpoint.read_text())} == {
        "first", "second",
    }
