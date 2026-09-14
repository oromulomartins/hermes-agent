"""Real Docker replacement/restoration on a synthetic SQLite volume, no VPS."""
import io
import base64
import hashlib
import subprocess
import time
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest
import uuid

from deploy import Deployment, DeploymentError, command
from probe import journey


@unittest.skipUnless(os.environ.get('HERMES_DEPLOY_DOCKER_TESTS') == '1', 'enable Docker integration explicitly')
class RehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.images = []
        for release, mutate in (('previous', '0'), ('candidate', '0'), ('incompatible', '1')):
            tag = 'hermes-deploy-test:' + uuid.uuid4().hex
            command('docker', 'build', '--build-arg', 'RELEASE=' + release, '--build-arg', 'MUTATE_DATA=' + mutate,
                    '-t', tag, str(Path(__file__).parent / 'fixtures'))
            cls.images.append(tag)

    @classmethod
    def tearDownClass(cls):
        for image in cls.images:
            command('docker', 'image', 'rm', image)

    def prepare(self, directory):
        deployment = Deployment(directory)
        deployment.previous_image = self.images[0]
        deployment.saved.mkdir(parents=True)
        db_path = Path(directory) / 'seed.db'
        with sqlite3.connect(db_path) as db:
            db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT)')
            db.execute("INSERT INTO sessions VALUES ('kept', 'history must survive')")
        with tarfile.open(deployment.saved / 'data.tar.gz', 'w:gz') as archive:
            archive.add(db_path, arcname='state.db')
            info = tarfile.TarInfo('sentinel.txt')
            payload = b'preserve other application files\n'
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        return deployment

    def test_real_candidate_is_replaced_with_previous_image_and_history_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            deployment = self.prepare(directory)
            deployment.rehearsal(self.images[1])
            evidence = deployment.receipt['rehearsal']
            self.assertEqual(len({e['container_id'] for e in evidence}), 3)
            self.assertEqual(evidence[0]['image'], evidence[2]['image'])
            self.assertNotEqual(evidence[0]['image'], evidence[1]['image'])
            self.assertTrue(deployment.receipt['rehearsal_preserved_records'])
            self.assertTrue(all(e['auth'] == 'password' and e['journey'] == 'passed' for e in evidence))
            self.assertNotIn('history must survive', json.dumps(deployment.receipt))

    def test_actual_failed_live_replacement_restores_image_configuration_and_history(self):
        password = 'synthetic-test-password'
        salt = b'synthetic-test-salt'
        digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
        encoded = 'scrypt$16384$8$1$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()

        class LocalDeployment(Deployment):
            def docker(self, *args, **kwargs):
                # Fixture images are local-only; all container/volume operations are real.
                if args[0] == 'pull':
                    return super().docker('image', 'inspect', args[1])
                return super().docker(*args, **kwargs)

            def wait_journey(self, container, url, password_override=None):
                for attempt in range(20):
                    try:
                        return self.probe(container, 'journey', url='http://127.0.0.1:4860',
                                          password=password_override or password)
                    except DeploymentError:
                        time.sleep(0.1)
                raise DeploymentError('Synthetic service failed its journey')

        with tempfile.TemporaryDirectory() as directory:
            name = 'hermes-transaction-' + uuid.uuid4().hex
            app = LocalDeployment(directory, container=name, volume=name)
            manifest = {'name': name, 'services': {'dashboard': {
                'image': '${IMAGE}', 'container_name': name, 'network_mode': 'none',
                'volumes': [name + ':/opt/data'],
                'environment': {'HERMES_HOME': '/opt/data', 'HERMES_DASHBOARD_PUBLIC_URL': 'https://fixture.invalid',
                                'HERMES_DASHBOARD_BASIC_AUTH_USERNAME': '${DASHBOARD_USERNAME}',
                                'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH': '${DASHBOARD_PASSWORD_HASH}',
                                'HERMES_DASHBOARD_BASIC_AUTH_SECRET': '${DASHBOARD_SESSION_SECRET}'}}},
                        'volumes': {name: {'name': name}}}
            app.compose.write_text(json.dumps(manifest))
            manifest['services']['dashboard']['environment']['FAIL_LIVE'] = '1'
            app.next_compose.write_text(json.dumps(manifest))
            for path, image, secret in ((app.env, self.images[0], 'old-session-secret'),
                                         (app.next_env, self.images[1], 'new-session-secret')):
                env = dict(os.environ, IMAGE=image, TRAEFIK_HOST='fixture.invalid', DASHBOARD_USERNAME='fixture',
                           DASHBOARD_PASSWORD_HASH=encoded, DASHBOARD_SESSION_SECRET=secret)
                path.write_bytes(subprocess.check_output(['bash', str(Path(__file__).parent / 'write-env.sh')], env=env))
            try:
                app.compose_command('up', '-d', 'dashboard')
                app.docker('exec', app.container, 'python', '-c',
                           "import sqlite3; d=sqlite3.connect('/opt/data/state.db'); d.execute('CREATE TABLE sessions(id TEXT)'); d.execute(\"INSERT INTO sessions VALUES ('preserved')\"); d.commit()")
                initial = app.inspect(app.container)
                original_config = app.compose.read_bytes()
                with self.assertRaises(DeploymentError):
                    app.execute()
                restored = app.inspect(app.container)
                self.assertEqual(app.receipt['status'], 'rolled_back')
                self.assertEqual(restored['Image'], initial['Image'])
                self.assertEqual(app.compose.read_bytes(), original_config)
                self.assertIn('old-session-secret', app.env.read_text())
                self.assertEqual(len({initial['Id'], app.receipt['candidate_container_id'], restored['Id']}), 3)
                self.assertEqual(app.probe(app.container, 'integrity')['state.db']['tables']['sessions']['count'], 1)
                self.assertTrue((app.saved / 'data.tar.gz').is_file())
            finally:
                app.docker('rm', '-f', app.container)
                app.docker('volume', 'rm', name)

    def test_incompatible_candidate_is_rejected_without_any_live_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            deployment = self.prepare(directory)
            with self.assertRaisesRegex(DeploymentError, 'compatibility'):
                deployment.rehearsal(self.images[2])
            self.assertTrue((deployment.saved / 'data.tar.gz').exists())
            self.assertFalse(deployment.env.exists())


class ProbeTransportTests(unittest.TestCase):
    def test_public_session_smoke_refuses_plain_http(self):
        with self.assertRaisesRegex(RuntimeError, 'HTTPS'):
            journey('http://example.test')
