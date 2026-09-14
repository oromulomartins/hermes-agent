"""Small external-system fixture for exercising Docker replacement and probes.

This is not the Hermes application. The published app is separately checked by CD.
"""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sqlite3

if os.environ.get('MUTATE_DATA') == '1':
    with sqlite3.connect('/opt/data/state.db') as db:
        db.execute('DELETE FROM sessions')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, body, cookie=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        if os.environ.get('FAIL_LIVE') == '1':
            self.respond(503, {})
            return
        if self.path == '/api/health':
            self.respond(200, {'auth_required': True})
        elif self.headers.get('Cookie') != 'fixture_session=valid':
            self.respond(401, {})
        elif self.path == '/api/auth/me':
            self.respond(200, {'user_id': os.environ['HERMES_DASHBOARD_BASIC_AUTH_USERNAME'], 'provider': 'basic'})
        else:
            self.respond(200, {})

    def do_POST(self):
        if self.path == '/auth/logout':
            self.respond(302, {}, 'fixture_session=; Max-Age=0; Path=/')
            return
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        _, n, r, p, salt, expected = os.environ['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH'].split('$')
        actual = hashlib.scrypt(body['password'].encode(), salt=base64.b64decode(salt),
                                n=int(n), r=int(r), p=int(p), dklen=32)
        ok = actual == base64.b64decode(expected) and body['username'] == os.environ['HERMES_DASHBOARD_BASIC_AUTH_USERNAME']
        self.respond(200 if ok else 401, {'ok': ok}, 'fixture_session=valid; Path=/' if ok else None)


HTTPServer(('0.0.0.0', 4860), Handler).serve_forever()
