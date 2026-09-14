"""In-container checks. Never emit credentials, tokens, database rows or HTTP bodies."""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def integrity(root=Path('/opt/data')):
    result = {}
    for name in ('state.db', 'projects.db'):
        path = root / name
        if not path.exists():
            continue
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=10) as db:
            if list(db.execute('PRAGMA quick_check')) != [('ok',)]:
                raise RuntimeError('SQLite integrity failed')
            schema = list(db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            rows = {}
            for table in tables:
                query = 'SELECT * FROM "' + table.replace('"', '""') + '"'
                # Startup maintenance updates timestamps and lazily records the FTS format.
                # Keep goal/loop/heartbeat metadata and all user records in the check.
                if name == 'state.db' and table == 'state_meta':
                    query += " WHERE key NOT IN ('last_auto_prune','last_vacuum','last_auto_archive','fts_storage_version')"
                encoded = [repr(row).encode() for row in db.execute(query)]
                rows[table] = {'count': len(encoded), 'sha256': hashlib.sha256(b'\n'.join(sorted(encoded))).hexdigest()}
            result[name] = {'schema': hashlib.sha256(repr(schema).encode()).hexdigest(), 'tables': rows}
    return result


def journey(url, password=None):
    if password is None and not url.startswith('https://'):
        raise RuntimeError('Public smoke requires verified HTTPS')
    if password is not None and urllib.parse.urlsplit(url).hostname != '127.0.0.1':
        raise RuntimeError('Synthetic password smoke requires container loopback')
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(jar))

    def request(path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url + path, data=payload, headers={'Content-Type': 'application/json', 'Origin': url})
        try:
            response = client.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read()

    status, body = request('/api/health')
    if status != 200 or json.loads(body).get('auth_required') is not True:
        raise RuntimeError('Health/auth gate failed')
    if request('/api/auth/me')[0] != 401:
        raise RuntimeError('Anonymous identity was not denied')
    username = os.environ['HERMES_DASHBOARD_BASIC_AUTH_USERNAME']
    if password is not None:
        status, body = request('/auth/password-login', {'provider': 'basic', 'username': username, 'password': password})
        if status != 200 or json.loads(body).get('ok') is not True:
            raise RuntimeError('Password login failed')
    else:
        # Existing deployments keep only the password hash. Exercise a short-lived
        # session through the real middleware, without extracting a production secret.
        from plugins.dashboard_auth.basic import BasicAuthProvider, _settings
        settings = _settings()
        settings['ttl_seconds'] = 60
        session = BasicAuthProvider(**settings)._mint_session(username)
        for name, value in (('__Host-hermes_session_at', session.access_token),
                            ('__Host-hermes_session_rt', session.refresh_token),
                            ('__Host-hermes_session_provider', 'basic')):
            host = urllib.parse.urlsplit(url).hostname
            jar.set_cookie(http.cookiejar.Cookie(0, name, value, None, False, host, False, False,
                                                 '/', True, True, int(time.time()) + 60, False, None, None, {}))
    status, body = request('/api/auth/me')
    if status != 200 or json.loads(body).get('user_id') != username or json.loads(body).get('provider') != 'basic':
        raise RuntimeError('Authenticated identity failed')
    if request('/api/sessions')[0] != 200 or request('/')[0] != 200:
        raise RuntimeError('Authenticated dashboard journey failed')
    if request('/auth/logout', {})[0] != 302:
        raise RuntimeError('Logout failed')
    if request('/api/auth/me')[0] != 401:
        raise RuntimeError('Logout did not clear the client session')
    return {'auth': 'password' if password is not None else 'signed-session', 'journey': 'passed'}


if __name__ == '__main__':
    try:
        args = json.load(sys.stdin)
        result = integrity() if args['check'] == 'integrity' else journey(args['url'], args.get('password'))
        print(json.dumps(result))
    except Exception as error:
        # Provider/config and HTTP exceptions can include sensitive payloads.
        print(json.dumps({'error': type(error).__name__}), file=sys.stderr)
        sys.exit(1)
