"""Transactional staging upgrade with a private backup and rollback rehearsal.

Only the named dashboard is replaced. No live volume is deleted or restored.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
PROBE = (HERE / 'probe.py').read_text()


class DeploymentError(RuntimeError):
    pass


def command(*args, data=None, timeout=300):
    process = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if process.returncode:
        # Docker/Compose error messages can include environment values.
        raise DeploymentError('Command failed: ' + args[0])
    return process.stdout


def atomic(path, data):
    temp = path.with_name(path.name + '.tmp')
    temp.write_bytes(data)
    temp.chmod(0o600)
    os.replace(temp, path)


def pin_env(content, image):
    lines = content.decode().splitlines()
    if sum(line.startswith('IMAGE=') for line in lines) != 1:
        raise DeploymentError('Expected exactly one IMAGE entry')
    return ('\n'.join('IMAGE=' + image if line.startswith('IMAGE=') else line for line in lines) + '\n').encode()


def preserve(before, after):
    # Fail closed on schema or stored-record changes in the cloned rehearsal.
    # A migration that needs another compatibility policy requires its own plan.
    if any(after.get(name) != state for name, state in before.items()):
        raise DeploymentError('Database compatibility/preservation check failed')


class Deployment:
    def __init__(self, directory, *, candidate_directory=None, container='hermes-agent-rm', volume='hermes-agent-rm-data'):
        self.directory = Path(directory).resolve()
        self.container, self.volume = container, volume
        self.run = uuid.uuid4().hex
        self.receipt = {'run': self.run, 'sha': os.environ.get('DEPLOY_SHA', ''), 'status': 'preflight', 'workflow_run': os.environ.get('DEPLOY_RUN_ID', '')}
        self.saved = self.directory / 'backups' / self.run
        self.env = self.directory / '.env'
        self.compose = self.directory / 'docker-compose.yml'
        inputs = Path(candidate_directory).resolve() if candidate_directory else self.directory
        self.next_env = inputs / '.env.next'
        self.next_compose = inputs / 'docker-compose.next.yml'

    def docker(self, *args, **kwargs):
        return command('docker', *args, **kwargs)

    def inspect(self, container):
        return json.loads(self.docker('inspect', container))[0]

    def compose_command(self, *args):
        return self.docker('compose', '--project-directory', str(self.directory), '--env-file', str(self.env),
                           '-f', str(self.compose), *args)

    def rendered(self, env, compose):
        definition = json.loads(self.docker('compose', '--project-directory', str(self.directory), '--env-file', str(env),
                                           '-f', str(compose), 'config', '--format', 'json'))
        service = definition['services']['dashboard']
        mounts = service.get('volumes', [])
        if (service.get('container_name') != self.container or len(mounts) != 1
                or mounts[0].get('type') != 'volume' or mounts[0].get('target') != '/opt/data'
                or definition.get('volumes', {}).get(mounts[0].get('source'), {}).get('name') != self.volume):
            raise DeploymentError('Deployment definition does not target the expected app volume/container')
        return service

    def probe(self, container, check, **kwargs):
        return json.loads(self.docker('exec', '-i', container, 'python', '-c', PROBE,
                                      data=json.dumps({'check': check, **kwargs}).encode(), timeout=90))

    def wait_journey(self, container, url, password=None):
        deadline = time.monotonic() + 180
        for attempt in range(30):
            try:
                return self.probe(container, 'journey', url=url, **({'password': password} if password else {}))
            except (DeploymentError, subprocess.TimeoutExpired):
                if attempt == 29 or time.monotonic() >= deadline:
                    raise DeploymentError('Dashboard journey did not become ready') from None
                time.sleep(2)

    def verify_live(self, expected_image, expected_env, baseline):
        actual = self.inspect(self.container)
        mounted = [m.get('Name') for m in actual['Mounts'] if m['Destination'] == '/opt/data']
        if actual['Image'] != expected_image or mounted != [self.volume] or not actual['State']['Running']:
            raise DeploymentError('Running image, volume or state mismatch')
        env = dict(item.split('=', 1) for item in actual['Config']['Env'])
        for key, value in expected_env.items():
            if env.get(key) != str(value).replace('$$', '$'):
                raise DeploymentError('Running configuration mismatch')
        result = self.wait_journey(self.container, env['HERMES_DASHBOARD_PUBLIC_URL'])
        preserve(baseline, self.probe(self.container, 'integrity'))
        return result

    def backup(self):
        writers = self.docker('ps', '--filter', 'volume=' + self.volume, '--format', '{{.Names}}').decode().splitlines()
        if writers != [self.container]:
            raise DeploymentError('Unexpected running writer on the application volume')
        size = int(self.docker('exec', self.container, 'du', '-sb', '/opt/data').split()[0])
        volume_free = int(self.docker('exec', self.container, 'python', '-c',
                                     "import shutil; print(shutil.disk_usage('/opt/data').free)"))
        if min(shutil.disk_usage(self.directory).free, volume_free) < 2 * size + 512 * 1024 * 1024:
            raise DeploymentError('Insufficient free space for backup and rehearsal')
        self.saved.mkdir(parents=True, mode=0o700)
        atomic(self.saved / '.env', self.env.read_bytes())
        atomic(self.saved / 'docker-compose.yml', self.compose.read_bytes())
        # Stop all app writers before archiving SQLite + WAL and other state.
        self.receipt['stage'] = 'consistent_backup'
        self.docker('stop', self.container)
        try:
            with (self.saved / 'data.tar.gz').open('xb') as archive:
                p = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--user', '0',
                                    '--volumes-from', self.container + ':ro', '--entrypoint', 'tar',
                                    self.previous_image, '-C', '/opt/data', '-czf', '-', '.'],
                                   stdout=archive, stderr=subprocess.PIPE, timeout=300)
                if p.returncode:
                    raise DeploymentError('Consistent backup failed')
            self.receipt['backup'] = self.run + '/data.tar.gz'
        finally:
            try:
                self.docker('start', self.container)
            except Exception:
                self.receipt['status'] = 'backup_restart_failed'
                raise

    def rehearsal(self, candidate):
        volume = 'hermes-rehearsal-' + self.run
        container = volume
        password = secrets.token_urlsafe(32)
        salt = secrets.token_bytes(16)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
        password_hash = 'scrypt$16384$8$1$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(dk).decode()
        env_file = self.saved / 'rehearsal.env'
        env_file.write_text('HERMES_HOME=/opt/data\nHERMES_WRITE_SAFE_ROOT=/opt/data\nHERMES_DISABLE_LAZY_INSTALLS=1\n'
                            'HERMES_DASHBOARD_BASIC_AUTH_USERNAME=rehearsal\n'
                            'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=' + password_hash + '\n'
                            'HERMES_DASHBOARD_BASIC_AUTH_SECRET=' + secrets.token_hex(32) + '\n')
        env_file.chmod(0o600)
        self.docker('volume', 'create', volume)
        active = False
        try:
            # Restore only into a new disposable volume. The live volume is never a target.
            with (self.saved / 'data.tar.gz').open('rb') as archive:
                p = subprocess.run(['docker', 'run', '--rm', '-i', '--network', 'none', '--user', '0',
                                    '-v', volume + ':/opt/data', '--entrypoint', 'tar', self.previous_image,
                                    '-C', '/opt/data', '-xzf', '-'], stdin=archive, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=300)
                if p.returncode:
                    raise DeploymentError('Backup restore into rehearsal volume failed')
            states = []
            # Run previous first to capture the copy, then candidate, then previous
            # again: this is replacement/restoration, not merely a failed pull.
            for image in (self.previous_image, candidate, self.previous_image):
                if active:
                    self.docker('rm', '-f', container)
                    active = False
                self.docker('run', '-d', '--name', container, '--network', 'none',
                            '--security-opt', 'no-new-privileges:true', '--memory', '2g', '--cpus', '2',
                            '-v', volume + ':/opt/data', '--env-file', str(env_file), image,
                            'dashboard', '--host', '0.0.0.0', '--port', '4860', '--no-open')
                active = True
                result = self.wait_journey(container, 'http://127.0.0.1:4860', password)
                state = self.probe(container, 'integrity')
                if states:
                    preserve(states[0], state)
                states.append(state)
                self.receipt.setdefault('rehearsal', []).append({'image': self.inspect(container)['Image'],
                                                                'container_id': self.inspect(container)['Id'], **result})
            self.receipt['rehearsal_preserved_records'] = True
        finally:
            if active:
                self.docker('rm', '-f', container)
            self.docker('volume', 'rm', volume)
            env_file.unlink(missing_ok=True)

    def execute(self, rehearse_only=False):
        os.umask(0o077)
        lock_path = self.directory / '.deploy.lock'
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                self.upgrade(rehearse_only)
            except Exception as error:
                self.receipt.setdefault('failure_type', type(error).__name__)
                if isinstance(error, DeploymentError):
                    self.receipt['failure_reason'] = str(error)
                if self.receipt['status'] not in ('rolled_back', 'rollback_failed', 'backup_restart_failed'):
                    self.receipt['status'] = 'failed_before_replace'
                raise
            finally:
                self.receipt['finished_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                receipts = self.directory / 'receipts'
                receipts.mkdir(exist_ok=True, mode=0o700)
                atomic(receipts / (self.run + '.json'), json.dumps(self.receipt, indent=2).encode())
                atomic(self.directory / 'receipt.json', json.dumps(self.receipt, indent=2).encode())

    def upgrade(self, rehearse_only):
        old = self.inspect(self.container)
        self.previous_image = old['Image']
        self.receipt['previous_image'] = self.previous_image
        previous_config = self.rendered(self.env, self.compose)
        baseline = self.probe(self.container, 'integrity')
        self.verify_live(self.previous_image, previous_config['environment'], baseline)
        candidate_config = self.rendered(self.next_env, self.next_compose)
        if candidate_config['environment'].get('HERMES_DASHBOARD_PUBLIC_URL') != previous_config['environment'].get('HERMES_DASHBOARD_PUBLIC_URL'):
            raise DeploymentError('Changing the public endpoint requires a separate plan')
        image = candidate_config['image']
        self.docker('pull', image, timeout=600)
        image_info = json.loads(self.docker('image', 'inspect', image))[0]
        candidate = image_info['Id']
        # Deploy an immutable local image ID; no second pull can change the artifact.
        self.receipt['candidate_image'] = candidate
        self.receipt['candidate_digests'] = image_info.get('RepoDigests', [])
        self.backup()
        self.receipt['stage'] = 'isolated_rehearsal'
        self.rehearsal(candidate)
        self.verify_live(self.previous_image, previous_config['environment'], baseline)
        if rehearse_only:
            self.receipt['status'] = 'rehearsal_passed'
            return
        try:
            atomic(self.env, pin_env(self.next_env.read_bytes(), candidate))
            atomic(self.compose, self.next_compose.read_bytes())
            self.receipt['stage'] = 'live_replace'
            self.receipt['status'] = 'replacing'
            self.compose_command('up', '-d', '--no-deps', '--pull', 'never', 'dashboard')
            self.receipt['candidate_container_id'] = self.inspect(self.container).get('Id')
            self.receipt['live_journey'] = self.verify_live(candidate, candidate_config['environment'], baseline)
            self.receipt['status'] = 'deployed'
        except Exception:
            # The old artifact was exercised against candidate-written cloned data.
            # Keep the live data; restoring an archive would discard intervening writes.
            try:
                atomic(self.env, pin_env((self.saved / '.env').read_bytes(), self.previous_image))
                atomic(self.compose, (self.saved / 'docker-compose.yml').read_bytes())
                self.compose_command('up', '-d', '--no-deps', '--pull', 'never', 'dashboard')
                self.receipt['recovery_journey'] = self.verify_live(self.previous_image, previous_config['environment'], baseline)
                self.receipt['restored_container_id'] = self.inspect(self.container).get('Id')
                self.receipt['status'] = 'rolled_back'
            except Exception:
                self.receipt['status'] = 'rollback_failed'
                raise DeploymentError('Rollback validation failed; preserve backup and inspect staging') from None
            raise DeploymentError('Candidate failed; previous version restored and validated') from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rehearse-only', action='store_true')
    parser.add_argument('--directory', type=Path, default=HERE)
    parser.add_argument('--candidate-dir', type=Path)
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise DeploymentError('Deployment interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        Deployment(args.directory, candidate_directory=args.candidate_dir).execute(args.rehearse_only)
    except Exception as error:
        print('Deployment failed (' + type(error).__name__ + '); see sanitized receipt.json', file=sys.stderr)
        sys.exit(1)
