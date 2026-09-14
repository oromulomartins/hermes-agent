"""Behavioral transaction tests; Docker rehearsal is covered in test_rehearsal.py."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from deploy import Deployment, DeploymentError, pin_env, preserve
from probe import integrity


class Scenario(Deployment):
    def __init__(self, directory, failure=None):
        super().__init__(directory)
        self.failure = failure
        self.events = []
        self.live = 'old'
        self.env.write_bytes(b'IMAGE=old\nDASHBOARD_SESSION_SECRET=old-secret\n')
        self.compose.write_bytes(b'old-compose')
        self.next_env.write_bytes(b'IMAGE=new\nDASHBOARD_SESSION_SECRET=new-secret\n')
        self.next_compose.write_bytes(b'new-compose')

    def inspect(self, container):
        return {'Image': self.live}

    def rendered(self, env, compose):
        return {'image': 'candidate', 'environment': {'secret': 'old' if env == self.env else 'new'}}

    def docker(self, *args, **kwargs):
        if args[0] == 'pull' and self.failure == 'pull':
            raise DeploymentError('pull')
        if args[:2] == ('image', 'inspect'):
            return json.dumps([{'Id': 'new', 'RepoDigests': ['example@sha256:new']}]).encode()
        return b''

    def probe(self, *args, **kwargs):
        return {'state.db': {'stable': True}}

    def verify_live(self, image, env, baseline):
        self.events.append('verify:' + image)
        if (image == 'new' and self.failure in ('smoke', 'recovery')) or (self.live == 'restored' and self.failure == 'recovery'):
            raise DeploymentError('unhealthy')
        return {'journey': 'passed'}

    def backup(self):
        self.saved.mkdir(parents=True)
        (self.saved / '.env').write_bytes(self.env.read_bytes())
        (self.saved / 'docker-compose.yml').write_bytes(self.compose.read_bytes())

    def rehearsal(self, candidate):
        self.events.append('rehearsal')
        if self.failure == 'rehearsal':
            raise DeploymentError('incompatible')

    def compose_command(self, *args):
        image = self.env.read_text().splitlines()[0].split('=', 1)[1]
        self.events.append('replace:' + image)
        self.live = 'restored' if image == 'old' else image
        if self.failure == 'startup' and image == 'new':
            raise DeploymentError('failed after replacement')


class DeploymentTests(unittest.TestCase):
    def test_failure_after_replacement_restores_full_config_and_reports_failed_job(self):
        for failure in ('smoke', 'startup'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                scenario = Scenario(directory, failure)
                with self.assertRaises(DeploymentError):
                    scenario.execute()
                self.assertEqual(scenario.env.read_bytes(), b'IMAGE=old\nDASHBOARD_SESSION_SECRET=old-secret\n')
                self.assertEqual(scenario.compose.read_bytes(), b'old-compose')
                self.assertEqual(scenario.events[-2:], ['replace:old', 'verify:old'])
                receipt = json.loads((Path(directory) / 'receipt.json').read_text())
                self.assertEqual(receipt['status'], 'rolled_back')
                self.assertNotIn('old-secret', json.dumps(receipt))
                self.assertEqual((Path(directory) / 'receipt.json').stat().st_mode & 0o777, 0o600)

    def test_pull_and_rehearsal_failures_do_not_replace_live_config(self):
        for failure in ('pull', 'rehearsal'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                scenario = Scenario(directory, failure)
                with self.assertRaises(DeploymentError):
                    scenario.execute()
                self.assertEqual(scenario.compose.read_bytes(), b'old-compose')
                self.assertFalse(any(event.startswith('replace:') for event in scenario.events))
                self.assertEqual(scenario.receipt['status'], 'failed_before_replace')

    def test_recovery_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = Scenario(directory, 'recovery')
            with self.assertRaises(DeploymentError):
                scenario.execute()
            self.assertEqual(scenario.receipt['status'], 'rollback_failed')

    def test_success_and_rehearsal_only_have_distinct_outcomes(self):
        for only in (False, True):
            with self.subTest(only=only), tempfile.TemporaryDirectory() as directory:
                scenario = Scenario(directory)
                scenario.execute(only)
                self.assertEqual(scenario.receipt['status'], 'rehearsal_passed' if only else 'deployed')
                self.assertEqual(scenario.compose.read_bytes(), b'old-compose' if only else b'new-compose')

    def test_schema_or_record_change_refuses_rollback_compatibility(self):
        before = {'state.db': {'schema': 'old', 'tables': {'sessions': 'original'}}}
        preserve(before, dict(before, new_database={}))
        for after in ({}, {'state.db': {'schema': 'new'}}, {'state.db': {'schema': 'old', 'tables': {'sessions': 'lost'}}}):
            with self.assertRaises(DeploymentError):
                preserve(before, after)
        with self.assertRaises(DeploymentError):
            pin_env(b'IMAGE=a\nIMAGE=b\n', 'c')


class DataIntegrityTests(unittest.TestCase):
    def test_startup_metadata_is_allowed_but_goal_data_and_history_are_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with sqlite3.connect(root / 'state.db') as db:
                db.execute('CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT)')
                db.execute("INSERT INTO state_meta VALUES ('goal:session', 'user goal')")
                db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT)')
                db.execute("INSERT INTO sessions VALUES ('kept', 'user history')")
            before = integrity(root)
            with sqlite3.connect(root / 'state.db') as db:
                db.execute("INSERT INTO state_meta VALUES ('fts_storage_version', '1')")
                db.execute("INSERT INTO state_meta VALUES ('last_auto_archive', '123')")
            preserve(before, integrity(root))
            with sqlite3.connect(root / 'state.db') as db:
                db.execute("UPDATE state_meta SET value='lost' WHERE key='goal:session'")
            with self.assertRaises(DeploymentError):
                preserve(before, integrity(root))
