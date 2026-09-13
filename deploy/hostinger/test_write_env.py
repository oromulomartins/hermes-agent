"""Run with python3 -m unittest discover -s deploy/hostinger -p 'test_*.py'.

Exercises the real writer and Docker Compose parser without starting containers.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent


class WriteEnvTests(unittest.TestCase):
    def write_env(self, password_hash, **overrides):
        env = os.environ.copy()
        env.update(IMAGE='example/hermes:test', TRAEFIK_HOST='example.test',
                   DASHBOARD_USERNAME='admin', DASHBOARD_PASSWORD_HASH=password_hash,
                   DASHBOARD_SESSION_SECRET='test-session-secret')
        env.update(overrides)
        return subprocess.run(['bash', str(ROOT / 'write-env.sh')], env=env,
                              capture_output=True, text=True)

    def test_compose_preserves_hash(self):
        password_hash = 'scrypt$16384$8$1$c2FsdA==$ZGlnZXN0'
        username = "admin${UNSET_REVIEW_VAR}'\\name"
        session_secret = "prefix${UNSET_REVIEW_VAR}\"'$$\\suffix\\"
        result = self.write_env(password_hash, DASHBOARD_USERNAME=username,
                                DASHBOARD_SESSION_SECRET=session_secret)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text(result.stdout)
            env = {k: v for k, v in os.environ.items()
                   if k not in ('IMAGE', 'TRAEFIK_HOST', 'DASHBOARD_USERNAME',
                                'DASHBOARD_PASSWORD_HASH', 'DASHBOARD_SESSION_SECRET')}
            parsed = subprocess.run(
                ['docker', 'compose', '--env-file', str(path), '-f',
                 str(ROOT / 'docker-compose.yml'), 'config', '--format', 'json'],
                env=env, capture_output=True, text=True, check=True)
        actual = json.loads(parsed.stdout)['services']['dashboard']['environment']
        # Compose escapes dollars in its serialized configuration for round trips.
        self.assertEqual(actual['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH']
                         .replace('$$', '$'), password_hash)
        self.assertEqual(actual['HERMES_DASHBOARD_BASIC_AUTH_USERNAME']
                         .replace('$$', '$'), username)
        self.assertEqual(actual['HERMES_DASHBOARD_BASIC_AUTH_SECRET']
                         .replace('$$', '$'), session_secret)
        entries = dict(line.split('=', 1) for line in result.stdout.splitlines())
        self.assertEqual(entries['IMAGE'], 'example/hermes:test')
        self.assertEqual(entries['TRAEFIK_HOST'], 'example.test')

    def test_rejects_multiline_values_before_writing(self):
        password_hash = 'scrypt$16384$8$1$c2FsdA==$ZGlnZXN0'
        for key in ('IMAGE', 'TRAEFIK_HOST', 'DASHBOARD_USERNAME', 'DASHBOARD_SESSION_SECRET'):
            for separator in ('\n', '\r'):
                with self.subTest(key=key, separator=separator):
                    result = self.write_env(password_hash, **{key: 'prefix' + separator + 'INJECTED=yes'})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, '')

    def test_rejects_malformed_and_injected_hashes_without_output(self):
        for value in ('plaintext', 'scrypt:16384:8:1:salt:digest',
                      "scrypt$16384$8$1$salt$hash'", 'scrypt$16384$8$1$salt$hash\nEXTRA=yes'):
            with self.subTest(value=value):
                result = self.write_env(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertNotIn(value, result.stderr)


if __name__ == '__main__':
    unittest.main()
